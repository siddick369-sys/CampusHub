import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CampuHub.settings')
django.setup()

from accounts.models import SubscriptionPlan

def seed_plans():
    # --- PLANS ÉTUDIANTS (Max 1,500 XAF) ---
    SubscriptionPlan.objects.update_or_create(
        code="FREE_STUDENT",
        defaults={
            "name": "Étudiant (Gratuit)",
            "role_target": "student",
            "price": 0,
            "max_cv_monthly": 1,
            "max_interviews_monthly": 1,
            "max_search_alerts": 1,
            "max_challenges_monthly": 0,
            "is_default": True,
            "description": "L'essentiel pour débuter sa recherche."
        }
    )
    SubscriptionPlan.objects.update_or_create(
        code="PRO_STUDENT",
        defaults={
            "name": "Étudiant Pro",
            "role_target": "student",
            "price": 1500,
            "max_cv_monthly": 15,
            "max_interviews_monthly": 20,
            "max_search_alerts": 10,
            "max_challenges_monthly": 5,
            "can_use_ai": True,
            "has_premium_badge": True,
            "description": "Boostez votre carrière avec l'IA et plus d'opportunités."
        }
    )

    # --- PLANS PRESTATAIRES (Max 3,000 XAF) ---
    SubscriptionPlan.objects.update_or_create(
        code="FREE_PROVIDER",
        defaults={
            "name": "Prestataire (Gratuit)",
            "role_target": "provider",
            "price": 0,
            "max_services_active": 1,
            "max_time_slots": 5,
            "max_search_alerts": 1,
            "max_challenges_monthly": 0,
            "is_default": True,
            "description": "Testez la plateforme avec votre premier service."
        }
    )
    SubscriptionPlan.objects.update_or_create(
        code="PRO_PROVIDER",
        defaults={
            "name": "Prestataire Pro",
            "role_target": "provider",
            "price": 1500,
            "max_services_active": 10,
            "max_time_slots": 30,
            "max_featured_services": 2,
            "max_search_alerts": 5,
            "max_challenges_monthly": 2,
            "can_use_ai": True,
            "has_premium_badge": True,
            "description": "Gérez plusieurs services et soyez plus visible."
        }
    )
    SubscriptionPlan.objects.update_or_create(
        code="EXPERT_PROVIDER",
        defaults={
            "name": "Prestataire Expert",
            "role_target": "provider",
            "price": 3000,
            "max_services_active": 50,
            "max_time_slots": 100,
            "max_featured_services": 10,
            "max_urgent_orders_per_day": 10,
            "max_search_alerts": 20,
            "max_challenges_monthly": 10,
            "can_use_ai": True,
            "has_premium_badge": True,
            "priority_matching": True,
            "description": "Le plan ultime pour les experts du campus."
        }
    )

    # --- PLANS ENTREPRISES (Max 5,000 XAF) ---
    SubscriptionPlan.objects.update_or_create(
        code="FREE_COMPANY",
        defaults={
            "name": "Entreprise (Basic)",
            "role_target": "company",
            "price": 0,
            "max_offers_monthly": 2,
            "max_search_alerts": 2,
            "max_challenges_monthly": 0,
            "is_default": True,
            "description": "Publiez vos premières offres gratuitement."
        }
    )
    SubscriptionPlan.objects.update_or_create(
        code="BUSINESS_COMPANY",
        defaults={
            "name": "Entreprise Business",
            "role_target": "company",
            "price": 2500,
            "max_offers_monthly": 20,
            "max_search_alerts": 10,
            "max_challenges_monthly": 5,
            "has_analytics": True,
            "has_premium_badge": True,
            "description": "Idéal pour les recrutements réguliers et le suivi analytique."
        }
    )
    SubscriptionPlan.objects.update_or_create(
        code="ELITE_COMPANY",
        defaults={
            "name": "Entreprise Elite",
            "role_target": "company",
            "price": 5000,
            "max_offers_monthly": 200,
            "max_search_alerts": 50,
            "max_challenges_monthly": 30,
            "can_use_ai": True,
            "has_premium_badge": True,
            "priority_matching": True,
            "has_analytics": True,
            "description": "Dominez le marché du recrutement avec tous nos outils."
        }
    )

if __name__ == "__main__":
    seed_plans()
    print("Plans refined and seeded successfully with new caps and balanced privileges.")
