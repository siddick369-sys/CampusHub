from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification, Message


def send_new_message_notification(message: Message):
    """
    Crée une notification + envoie un email au destinataire
    quand il reçoit un nouveau message.
    """
    conversation = message.conversation
    sender = message.sender

    # destinataire = l’autre personne dans la conversation
    if sender == conversation.student:
        recipient = conversation.company
    else:
        recipient = conversation.student

    # 🔔 Notification interne
    notif_text = (
        f"Nouveau message de {sender.username} "
        f"dans la conversation liée à « {conversation.application.offer.title} »."
    )

    Notification.objects.create(
        user=recipient,
        notif_type="message",
        message=notif_text,
        offer=conversation.application.offer,
        application=conversation.application,
    )

    # 📧 Email
    if recipient.email:
        subject = "Nouveau message sur CampusHub 💬"

        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
        try:
            html_message = render_to_string(
                "emails/new_message.html",
                {
                    "recipient": recipient,
                    "sender": sender,
                    "conversation": conversation,
                    "message": message,
                    "base_url": base_url,
                }
            )
        except Exception:
            html_message = None

        text_message = (
            f"Bonjour {recipient.username},\n\n"
            f"Vous avez reçu un nouveau message de {sender.username} "
            f"à propos de l'offre « {conversation.application.offer.title} ».\n\n"
            f"Connectez-vous à CampusHub pour répondre : {base_url}/stages/messages/{conversation.pk}/\n\n"
            "L'équipe CampusHub."
        )

        send_mail(
            subject=subject,
            message=text_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient.email],
            fail_silently=True,
            html_message=html_message,
        )