from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from stages.models import Application, Notification


class Command(BaseCommand):
    help = "Envoie un rappel pour les candidatures non lues (non consultées) aux entreprises."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🔔 Recherche des candidatures non lues à rappeler…"))

        today = timezone.now()
        cutoff = today - timedelta(days=3)  # ex : plus de 3 jours

        # Candidatures :
        # - statut = 'submitted' (pas encore consultées)
        # - créées il y a plus de X jours
        # - aucun rappel encore envoyé
        applications = (
            Application.objects
            .select_related('offer', 'offer__company')
            .filter(
                status='submitted',
                created_at__lte=cutoff,
                reminder_sent=False,
                offer__is_active=True,
                offer__status='published',
            )
        )

        if not applications.exists():
            self.stdout.write(self.style.SUCCESS("Aucune candidature à rappeler."))
            return

        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

        count = 0
        for app in applications:
            offer = app.offer
            company = offer.company

            # Message texte pour Notification et fallback email
            message_text = (
                f"Vous avez une candidature non traitée pour l'offre « {offer.title} ».\n\n"
                f"- Candidat : {app.student.username}\n"
                f"- Date de candidature : {app.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Connectez-vous à votre espace pour consulter cette candidature."
            )

            # 🔔 Notification interne
            Notification.objects.create(
                user=company,
                notif_type='new_application',  # ou 'general'
                message=message_text,
                offer=offer,
                application=app,
            )

            # 📧 Email HTML
            if company.email:
                subject = f"Rappel : candidature non traitée pour « {offer.title} »"

                html_message = render_to_string(
                    "emails/unread_application_reminder.html",
                    {
                        "company": company,
                        "offer": offer,
                        "application": app,
                        "base_url": base_url,
                    }
                )

                try:
                    send_mail(
                        subject=subject,
                        message=message_text,  # fallback texte
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=[company.email],
                        fail_silently=True,
                        html_message=html_message,
                    )
                except Exception:
                    # On n'arrête pas la commande pour des erreurs d'email.
                    pass

            # marquer le rappel comme envoyé
            app.reminder_sent = True
            app.save(update_fields=['reminder_sent'])

            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count} rappel(s) envoyé(s)."))