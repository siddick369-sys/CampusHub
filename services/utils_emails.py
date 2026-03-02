# services/utils_emails.py

from django.conf import settings
from django.template.loader import render_to_string

# On importe la classe de Threading définie dans utils_notifications
# Assurez-vous que utils_notifications.py contient bien la classe EmailThread
from .utils_notifications import EmailThread
from .tasks import send_plain_email_service_task, send_html_email_service_task
from django.db import transaction


def send_favorite_service_expiring_email(favorite, order):
    """
    Envoie un email (Async) à l'utilisateur pour un service favori
    dont une commande active est presque à échéance.
    """
    user = favorite.user
    service = favorite.service

    if not user.email:
        return

    site_name = getattr(settings, "SITE_NAME", "CampusHub")
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

    subject = f"[{site_name}] Un de vos services favoris est presque à échéance"

    message = (
        f"Bonjour {user.first_name or user.username},\n\n"
        f"Un de vos services favoris approche de sa date limite de commande :\n\n"
        f"- Service : {service.title}\n"
        f"- Délai de la commande en cours : jusqu'au {order.due_date.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Il se peut que ce service devienne indisponible, soit modifié ou désactivé après cette date.\n\n"
        f"Vous pouvez consulter ce service ici : {base_url}/services/{service.slug}/\n\n"
        f"Cordialement,\nL'équipe {site_name}"
    )
    transaction.on_commit(
    lambda: send_plain_email_service_task.delay(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        [user.email]
    )
)



def notify_service_provider_new_urgent_order(order):
    """
    Envoie un email spécial URGENT (Async) au prestataire
    UNIQUEMENT si son trust_score > 80.
    """
    provider = order.provider
    profile = getattr(provider, "profile", None)

    if not profile:
        return

    # ✅ seulement prestataires avec bon score
    if profile.trust_score is None or profile.trust_score <= 80:
        return

    # respect des préférences emails
    if not getattr(profile, "service_email_as_provider", True):
        return

    subject = f"[URGENT] Nouvelle commande urgente pour « {order.service_title_snapshot} »"
    
    # Construction du message texte
    lines = [
        f"Bonjour {profile.full_name or provider.username},",
        "",
        "Vous avez reçu une nouvelle COMMANDE URGENTE sur CampusHub :",
        f"- Service : {order.service_title_snapshot}",
        f"- Client : {order.client.username}",
    ]

    if order.total_price:
        lines.append(f"- Prix indicatif total : {order.total_price} {order.currency}")
    
    if order.is_urgent:
        lines.append("⚠ Cette commande est marquée comme URGENTE.")

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    order_url = f"{base_url}/services/orders/{order.id}/"

    lines.append("")
    lines.append("Connectez-vous rapidement à votre espace pour répondre :")
    lines.append(order_url)

    message = "\n".join(lines)
    transaction.on_commit(
    lambda: send_plain_email_service_task.delay(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@campushub.local"),
        [provider.email]
    )
)


def send_subscription_changed_email(provider, old_plan, new_plan):
    """
    Envoie un email (Async) au prestataire pour confirmer le changement de plan.
    """
    if not provider or not provider.email:
        return

    context = {
        "user": provider,
        "old_plan": old_plan,
        "new_plan": new_plan,
        "site_name": getattr(settings, "SITE_NAME", "CampusHub"),
        "site_domain": getattr(settings, "SITE_DOMAIN", "localhost:8000"),
    }

    subject = f"[{context['site_name']}] Ton abonnement a été mis à jour"

    message_txt = render_to_string(
        "emails/subscription_changed_email.txt",
        context,
    )
    
    message_html = None
    try:
        message_html = render_to_string(
            "emails/subscription_changed_email.html",
            context,
        )
    except Exception:
        pass
    
    transaction.on_commit(
    lambda: send_html_email_service_task.delay(
        subject,
        message_txt,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        [provider.email],
        message_html
    )
)
