from django.core.management.base import BaseCommand
from django.core.mail import mail_admins

from accounts.models import Profile
from accounts.utils_trust import recompute_trust_score_for_profile


class Command(BaseCommand):
    help = "Recalcule le trust_score pour tous les profils et envoie un email aux admins si certains sont en zone rouge."

    def handle(self, *args, **options):
        profiles = Profile.objects.select_related("user").all()
        total = profiles.count()
        red_zone_profiles = []

        self.stdout.write(f"Recalcul du trust_score pour {total} profils...")

        for profile in profiles:
            new_score = recompute_trust_score_for_profile(profile)
            self.stdout.write(
                f"- {profile.user.username} → trust_score = {new_score}"
            )
            if new_score <= 20:
                red_zone_profiles.append(profile)

        # 🔔 Email aux admins si profils en zone rouge
        if red_zone_profiles:
            body_lines = []
            for p in red_zone_profiles:
                body_lines.append(
                    f"- {p.user.username} (id={p.user.id}, email={p.user.email}) "
                    f"→ trust_score={p.trust_score}"
                )

            message = (
                "Certains utilisateurs sont en zone rouge (trust_score <= 20) :\n\n"
                + "\n".join(body_lines)
            )

            mail_admins(
                subject="CampusHub – Alertes trust_score (zone rouge)",
                message=message,
                fail_silently=False,  # pour voir les erreurs si ça plante
            )

            self.stdout.write(self.style.WARNING(
                f"{len(red_zone_profiles)} profils en zone rouge. Email envoyé aux admins."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Aucun profil en zone rouge. Aucun email envoyé."
            ))