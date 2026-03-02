# incubateur/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import ChallengeEntreprise, ChallengeSearchAlert
from .utils import EmailThread # Ton utilitaire de threading

from .models import ProjetInnovation, ProjetSearchAlert


@receiver(post_save, sender=ProjetInnovation)
def check_alerts_for_new_project(sender, instance, created, **kwargs):

    if created:

        matching_alerts = ProjetSearchAlert.objects.filter(
            Q(query__icontains=instance.titre) |
            Q(query__in=instance.description_courte.split())
        ).select_related('user__user')

        users_to_notify = set()

        for alerte in matching_alerts:
            keyword = alerte.query.lower()
            text_corpus = (instance.titre + " " + instance.description_courte).lower()

            if keyword in text_corpus:
                users_to_notify.add(alerte.user)

        for profile in users_to_notify:
            if profile.user.email:
                subject = f"🚀 Nouvelle Startup CampusHub : {instance.titre}"
                message = f"""Bonjour {profile.full_name},

Un nouveau projet étudiant correspond à votre recherche.

Projet : {instance.titre}
Pitch : {instance.description_courte}
Porteur : {instance.porteur.full_name}

Découvrez-le ici : https://campushub.com/incubation/projets/

L'équipe CampusHub
"""

                transaction.on_commit(
                    lambda email=profile.user.email, s=subject, m=message:
                    send_alert_email.delay(s, m, email)
                )
                
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from django.db import transaction
from .models import ChallengeEntreprise, ChallengeSearchAlert
from .tasks import send_alert_email


@receiver(post_save, sender=ChallengeEntreprise)
def check_alerts_for_new_challenge(sender, instance, created, **kwargs):
    if created and instance.is_active:

        matching_alerts = ChallengeSearchAlert.objects.filter(
            Q(query__icontains=instance.titre) |
            Q(query__in=instance.description.split())
        ).select_related('user__user')

        users_to_notify = set()

        for alerte in matching_alerts:
            keyword = alerte.query.lower()
            text_corpus = (instance.titre + " " + instance.description).lower()

            if keyword in text_corpus:
                users_to_notify.add(alerte.user)

        for profile in users_to_notify:
            if profile.user.email:
                subject = "🔔 Alerte CampusHub : Un nouveau challenge correspond à votre recherche !"
                message = f"""Bonjour {profile.full_name},

Bonne nouvelle ! Une entreprise vient de publier un challenge qui pourrait vous intéresser.

Challenge : {instance.titre}
Entreprise : {instance.entreprise.company_name}
Récompense : {instance.recompense}

Vous aviez une alerte pour des recherches similaires.
Cliquez ici pour voir le détail : https://campushub.com/incubation/challenges/{instance.pk}/

Bonne chance !
L'équipe CampusHub
"""

                transaction.on_commit(
                    lambda email=profile.user.email, s=subject, m=message:
                    send_alert_email.delay(s, m, email)
                )
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import ProjetInnovation, ParticipationChallenge
from accounts.models import Badge, UserBadge, Profile

# --- 1. BADGE "POPULARITÉ" (Trigger sur les Likes) ---
@receiver(m2m_changed, sender=ProjetInnovation.likes.through)
def verifier_badge_likes(sender, instance, action, **kwargs):
    if action == "post_add":
        # instance est le ProjetInnovation
        if instance.total_likes >= 10: # Seuil à 10 likes
            badge_pop, _ = Badge.objects.get_or_create(
                nom="Projet Tendance 🔥",
                defaults={'description': "A obtenu plus de 10 likes sur un projet."}
            )
            UserBadge.objects.get_or_create(user=instance.porteur, badge=badge_pop)
            
            # Bonus réputation
            instance.porteur.trust_score += 5
            instance.porteur.save()

# --- 2. BADGE "VAINQUEUR" (Trigger sur Challenge) ---
@receiver(post_save, sender=ParticipationChallenge)
def verifier_badge_victoire(sender, instance, created, **kwargs):
    if instance.est_vainqueur:
        badge_win, _ = Badge.objects.get_or_create(
            nom="Champion IUT 🏆",
            defaults={'description': "A remporté un challenge entreprise."}
        )
        UserBadge.objects.get_or_create(user=instance.candidat, badge=badge_win)
        
        # Gros bonus réputation
        instance.candidat.trust_score += 50
        instance.candidat.save()