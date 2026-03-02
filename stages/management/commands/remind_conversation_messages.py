from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.core.mail import send_mail

from stages.models import Conversation, Message, Notification


class Command(BaseCommand):
    help = "Envoie des rappels intelligents sur les conversations (messages non répondus / non lus)."

    def handle(self, *args, **options):
        now = timezone.now()
        company_cutoff = now - timezone.timedelta(days=2)  # X jours sans réponse de l'entreprise
        student_cutoff = now - timezone.timedelta(days=1)  # 1 jour sans lecture par l'étudiant

        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

        conversations = (
            Conversation.objects
            .filter(is_active=True)
            .select_related("student", "company", "application__offer")
        )

        company_reminders = 0
        student_reminders = 0

        for conv in conversations:
            last_msg = (
                Message.objects
                .filter(conversation=conv)
                .order_by("-created_at")
                .first()
            )
            if not last_msg:
                continue

            # ------------------------------------------------------
            # 1️⃣ Rappel à l'entreprise : dernier message de l'étudiant
            #     → pas de réponse depuis >= 2 jours
            # ------------------------------------------------------
            if (
                last_msg.sender_id == conv.student_id
                and last_msg.created_at <= company_cutoff
            ):
                # éviter le spam : on ne renvoie pas plusieurs fois pour le même message
                if (
                    conv.company_last_reminder_at is None
                    or conv.company_last_reminder_at < last_msg.created_at
                ):
                    student_name = getattr(conv.student.profile, "full_name", None) or conv.student.username
                    offer = conv.application.offer if conv.application else None
                    offer_title = offer.title if offer else "une offre"

                    notif_text = (
                        f"Vous avez un message non répondu de {student_name} "
                        f"dans la conversation à propos de « {offer_title} »."
                    )

                    # 🔔 Notification interne
                    Notification.objects.create(
                        user=conv.company,
                        notif_type="general",  # tu peux ajouter un type 'message_reminder' plus tard
                        message=notif_text,
                        offer=offer,
                        application=conv.application,
                    )

                    # 📧 Email à l'entreprise (si email défini)
                    if conv.company.email:
                        subject = "CampusHub – Message non répondu d'un étudiant"
                        conversation_url = f"{base_url}/stages/messages/{conv.id}/"

                        email_body = (
                            f"Bonjour,\n\n"
                            f"Vous avez un message non répondu de {student_name} "
                            f"concernant « {offer_title} » sur CampusHub.\n\n"
                            f"Pour répondre, connectez-vous à votre espace et ouvrez la conversation :\n"
                            f"{conversation_url}\n\n"
                            f"Ceci est un rappel automatique de CampusHub."
                        )

                        try:
                            send_mail(
                                subject,
                                email_body,
                                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                                [conv.company.email],
                                fail_silently=True,
                            )
                        except Exception:
                            # on ignore les erreurs d'email pour ne pas casser la commande
                            pass

                    conv.company_last_reminder_at = now
                    conv.save(update_fields=["company_last_reminder_at"])
                    company_reminders += 1

            # ------------------------------------------------------
            # 2️⃣ Rappel à l'étudiant : message important non lu
            #     (entretien, rendez-vous...) depuis >= 1 jour
            # ------------------------------------------------------
            unread_important_exists = (
                Message.objects
                .filter(
                    conversation=conv,
                    is_read=False,
                    sender=conv.company,
                    created_at__lte=student_cutoff,
                )
                .filter(
                    Q(text__icontains="entretien") |
                    Q(text__icontains="interview") |
                    Q(text__icontains="rdv") |
                    Q(text__icontains="rendez-vous")
                )
                .exists()
            )

            if unread_important_exists:
                if (
                    conv.student_last_reminder_at is None
                    or conv.student_last_reminder_at < student_cutoff
                ):
                    company_name = getattr(conv.company.profile, "company_name", None) or conv.company.username
                    offer = conv.application.offer if conv.application else None
                    offer_title = offer.title if offer else "une offre"

                    notif_text = (
                        f"Tu as peut-être manqué un message important de {company_name} "
                        f"concernant « {offer_title} »."
                    )

                    # 🔔 Notification interne
                    Notification.objects.create(
                        user=conv.student,
                        notif_type="general",
                        message=notif_text,
                        offer=offer,
                        application=conv.application,
                    )

                    # 📧 Email à l'étudiant (si email défini)
                    if conv.student.email:
                        subject = "CampusHub – Message important non lu"
                        conversation_url = f"{base_url}/stages/messages/{conv.id}/"

                        email_body = (
                            f"Salut {conv.student.username},\n\n"
                            f"Tu as peut-être manqué un message important de {company_name} "
                            f"à propos de « {offer_title} » sur CampusHub.\n\n"
                            f"Pour le lire, connecte-toi à ton compte et ouvre la conversation :\n"
                            f"{conversation_url}\n\n"
                            f"Ceci est un rappel automatique de CampusHub."
                        )

                        try:
                            send_mail(
                                subject,
                                email_body,
                                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                                [conv.student.email],
                                fail_silently=True,
                            )
                        except Exception:
                            pass

                    conv.student_last_reminder_at = now
                    conv.save(update_fields=["student_last_reminder_at"])
                    student_reminders += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Rappels envoyés : {company_reminders} côté entreprises, {student_reminders} côté étudiants."
            )
        )