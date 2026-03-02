from django.utils import timezone
from datetime import timedelta
from .models import Profile, Subscription, SubscriptionPlan, UsageTracking

class SubscriptionManager:
    @staticmethod
    def get_or_create_free_plan(role):
        """Récupère ou crée le plan gratuit par défaut pour un rôle."""
        plan_name = f"Gratuit {role.capitalize()}"
        plan, created = SubscriptionPlan.objects.get_or_create(
            name=plan_name,
            role_target=role,
            defaults={
                "price": 0,
                "max_cv_monthly": 1,
                "max_interviews_monthly": 1,
                "max_tests_monthly": 1,
                "max_projects_monthly": 1,
                "max_offers_monthly": 1,
                "can_use_ai": True
            }
        )
        return plan

    @staticmethod
    def activate_trial(user):
        """Active le trial de 30 jours pour un nouvel utilisateur."""
        profile = user.profile
        if profile.trial_consumed:
            return False
        
        # Définir les dates
        profile.first_login_at = timezone.now()
        profile.trial_expiration_date = profile.first_login_at + timedelta(days=30)
        profile.trial_consumed = True
        profile.save(update_fields=['first_login_at', 'trial_expiration_date', 'trial_consumed'])

        # Assigner un plan "Premium Trial" (on le crée s'il n'existe pas)
        trial_plan, _ = SubscriptionPlan.objects.get_or_create(
            name="Trial Premium",
            defaults={
                "price": 0,
                "max_interviews_monthly": 5,
                "max_tests_monthly": 5,
                "max_cv_monthly": 3,
                "max_projects_monthly": 2,
                "can_use_ai": True,
                "has_premium_badge": True
            }
        )

        Subscription.objects.update_or_create(
            user=user,
            defaults={
                "plan": trial_plan,
                "is_trial": True,
                "is_active": True,
                "end_date": profile.trial_expiration_date
            }
        )
        return True

class UsageManager:
    @staticmethod
    def get_limit_for_action(user, action_type):
        """Retourne la limite du quota pour l'action donnée selon l'abonnement actuel."""
        sub = getattr(user, 'user_subscription', None)
        if not sub or not sub.is_active or sub.is_expired:
            # Fallback sur plan gratuit par défaut
            return 1 # Valeur par défaut minimaliste
        
        plan = sub.plan
        mapping = {
            'cv_ia': plan.max_cv_monthly,
            'interview_ia': plan.max_interviews_monthly,
            'test_ia': plan.max_tests_monthly,
            'project_publication': plan.max_projects_monthly,
            'challenge_publication': plan.max_challenges_monthly,
            'search_alerts_count': plan.max_search_alerts,
        }
        return mapping.get(action_type, 0)

    @staticmethod
    def get_active_search_alerts_count(user):
        """Compte le nombre total d'alertes de recherche actives toutes catégories confondues."""
        from incubation.models import ChallengeSearchAlert, ProjetSearchAlert
        from stages.models import JobSearchAlert
        from services.models import ServiceSearchAlert
        
        count = 0
        profile = getattr(user, 'profile', None)
        if profile:
            count += ChallengeSearchAlert.objects.filter(user=profile).count()
            count += ProjetSearchAlert.objects.filter(user=profile).count()
            count += JobSearchAlert.objects.filter(student=user).count()
            count += ServiceSearchAlert.objects.filter(user=user).count()
        return count

    @staticmethod
    def is_action_allowed(user, action_type):
        """Vérifie si l'utilisateur peut encore effectuer l'action (trial/sub quotas)."""
        limit = UsageManager.get_limit_for_action(user, action_type)
        
        # Cas spécial pour les alertes de recherche (limite sur le nombre total actif)
        if action_type == 'search_alerts_count':
            return UsageManager.get_active_search_alerts_count(user) < limit

        # On récupère le tracking pour le mois en cours pour les actions mensuelles
        now = timezone.now()
        tracking, _ = UsageTracking.objects.get_or_create(
            user=user,
            action_type=action_type,
            reset_date=now.date().replace(day=1), # Début du mois
        )
        
        return tracking.count < limit

    @staticmethod
    def increment_usage(user, action_type):
        """Incrémente le compteur d'utilisation. (Ignoré pour search_alerts_count car géré par les modèles réels)"""
        if action_type == 'search_alerts_count':
            return # Les alertes sont de vrais objets, on ne suit pas leur incrément ici
            
        now = timezone.now()
        tracking, _ = UsageTracking.objects.get_or_create(
            user=user,
            action_type=action_type,
            reset_date=now.date().replace(day=1),
        )
        tracking.count += 1
        tracking.save(update_fields=['count'])

    @staticmethod
    def get_usage_stats(user):
        """Retourne un dictionnaire des statistiques d'utilisation actuelle vs limites."""
        now = timezone.now()
        actions = {
            'cv_ia': 'CV Assistés',
            'interview_ia': 'Simulations d\'entretien',
            'test_ia': 'Tests de compétences',
            'project_publication': 'Projets publiés',
            'offer_publication': 'Offres publiées',
            'challenge_publication': 'Challenges publiés',
            'search_alerts_count': 'Alertes de recherche'
        }
        stats = {}

        for action, label in actions.items():
            limit = UsageManager.get_limit_for_action(user, action)
            
            if action == 'search_alerts_count':
                count = UsageManager.get_active_search_alerts_count(user)
            else:
                tracking = UsageTracking.objects.filter(
                    user=user,
                    action_type=action,
                    reset_date=now.date().replace(day=1)
                ).first()
                count = tracking.count if tracking else 0
                
            stats[action] = {
                'label': label,
                'count': count,
                'limit': limit,
                'percent': min(100, int((count / limit) * 100)) if limit > 0 else 0
            }
        return stats
