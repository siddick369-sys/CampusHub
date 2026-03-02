# services/utils_notifications.py

import threading
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.db.models import Q

# Import des modèles (adaptez le chemin si nécessaire)
from stages.models import Notification
from .models import ServiceSearchAlert, ServiceOffer, ServiceOrder, ProviderFollow


# -------------------------------------------------------------------
#  CLASSE UTILITAIRE : THREADING (ASYNCHRONE)
# -------------------------------------------------------------------

class EmailThread(threading.Thread):
    """
    Classe utilitaire pour envoyer des emails en arrière-plan (Asynchrone).
    Permet de ne pas bloquer l'utilisateur lors de l'exécution de la vue.
    """
    def __init__(self, subject, message, from_email, recipient_list, html_message=None, fail_silently=True):
        self.subject = subject
        self.message = message
        self.from_email = from_email
        self.recipient_list = recipient_list
        self.html_message = html_message
        self.fail_silently = fail_silently
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                self.from_email,
                self.recipient_list,
                fail_silently=self.fail_silently,
                html_message=self.html_message
            )
        except Exception as e:
            # En production, utilisez un logger : logging.error(f"Email error: {e}")
            print(f"Erreur d'envoi d'email : {e}")


# -------------------------------------------------------------------
#  HELPERS
# -------------------------------------------------------------------

def _send_simple_email(to_email, subject, message):
    """
    Petit helper pour envoyer un email texte simple via Threading.
    """
    if not to_email:
        return

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    
    # Utilisation du Threading pour l'envoi
    EmailThread(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[to_email],
        fail_silently=True
    ).start()


def _build_absolute_url(path: str) -> str:
    """
    Construit une URL absolue simple.
    Utilise SITE_BASE_URL (ou SITE_URL) des settings, sinon fallback.
    """
    base = getattr(settings, "SITE_BASE_URL", getattr(settings, "SITE_URL", "http://localhost:8000")).rstrip("/")
    if not base:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path


# -------------------------------------------------------------------
#  NOTIFICATIONS : COMMANDES (ORDERS)
# -------------------------------------------------------------------

def notify_service_provider_new_order(order: ServiceOrder):
    """
    Notifie le prestataire d'une nouvelle commande :
      - Notification interne
      - Email (si autorisé dans son profil)
    """
    provider = order.provider
    if not provider:
        return

    profile = getattr(provider, "profile", None)
    
    # Construction du message (Version détaillée combinée)
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    order_url = f"{base_url}/services/orders/{order.id}/"
    site_name = getattr(settings, "SITE_NAME", "CampusHub")

    message_text = (
        f"Bonjour {provider.username},\n\n"
        f"Vous avez reçu une nouvelle commande pour votre service :\n"
        f"« {order.service_title_snapshot} ».\n\n"
        f"Détails de la commande :\n"
        f"- Client : {order.client.username}\n"
        f"- Montant : {order.agreed_price} {order.currency}\n"
        f"- Date limite : {order.due_date}\n\n"
        f"Vous pouvez consulter la commande ici :\n"
        f"{order_url}\n\n"
        f"Cordialement,\n"
        f"L'équipe {site_name}"
    )

    # 🔔 Notification interne
    Notification.objects.create(
        user=provider,
        notif_type="service_order_new", # Utilisation du type spécifique s'il existe, sinon 'general'
        message=f"Vous avez reçu une nouvelle commande pour votre service « {order.service_title_snapshot} ».",
        offer=None,
        application=None,
    )

    # 📧 Email au prestataire (Vérification des préférences)
    if provider.email and profile:
        # On vérifie si l'utilisateur veut recevoir les emails en tant que prestataire
        if getattr(profile, "service_email_as_provider", True):
            subject = f"[{site_name}] Nouvelle commande pour « {order.service_title_snapshot} »"
            
            # Envoi Asynchrone
            _send_simple_email(provider.email, subject, message_text)


def notify_client_order_status_change(order, old_status, new_status):
    """
    Notifie le CLIENT quand le statut de la commande change.
    """
    client = order.client
    profile = getattr(client, "profile", None)

    if not client.email or not profile:
        return
    # Vérification préférence client
    if not getattr(profile, "service_email_as_client", True):
        return

    site_name = getattr(settings, "SITE_NAME", "CampusHub")
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    order_url = f"{base_url}/services/orders/{order.id}/"

    subject = f"[{site_name}] Mise à jour de votre commande"
    body = ""

    if new_status == "accepted":
        subject = f"[{site_name}] Votre commande a été acceptée ✅"
        body = (
            f"Bonjour {client.username},\n\n"
            f"Votre commande pour le service « {order.service_title_snapshot} » "
            f"a été acceptée par le prestataire {order.provider.username}.\n\n"
            f"Suivre la commande : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    elif new_status == "cancelled_by_provider":
        subject = f"[{site_name}] Votre commande a été refusée ❌"
        body = (
            f"Bonjour {client.username},\n\n"
            f"Votre commande pour le service « {order.service_title_snapshot} » "
            f"a été refusée / annulée par le prestataire.\n\n"
            f"Détails : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    elif new_status == "completed":
        subject = f"[{site_name}] Votre commande est terminée ✅"
        body = (
            f"Bonjour {client.username},\n\n"
            f"La commande pour le service « {order.service_title_snapshot} » "
            f"est maintenant marquée comme terminée.\n\n"
            f"Merci d'avoir utilisé {site_name}.\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    elif new_status == "provider_marked_complete":
        subject = f"[{site_name}] Le prestataire a marqué la commande comme terminée"
        body = (
            f"Bonjour {client.username},\n\n"
            f"Le prestataire a marqué la commande « {order.service_title_snapshot} » comme terminée.\n\n"
            f"Merci de confirmer la fin du travail ici : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    else:
        # Fallback
        body = (
            f"Bonjour {client.username},\n\n"
            f"Le statut de votre commande pour « {order.service_title_snapshot} » "
            f"a été mis à jour ({new_status}).\n\n"
            f"Voir la commande : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )

    _send_simple_email(client.email, subject, body)


def notify_provider_order_status_change(order, old_status, new_status):
    """
    Notifie le PRESTATAIRE quand le statut change (ex: annulation client).
    """
    provider = order.provider
    profile = getattr(provider, "profile", None)

    if not provider.email or not profile:
        return
    if not getattr(profile, "service_email_as_provider", True):
        return

    site_name = getattr(settings, "SITE_NAME", "CampusHub")
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    order_url = f"{base_url}/services/orders/{order.id}/"

    subject = f"[{site_name}] Mise à jour d'une commande"
    body = ""

    if new_status == "cancelled_by_client":
        subject = f"[{site_name}] Une commande a été annulée par le client"
        body = (
            f"Bonjour {provider.username},\n\n"
            f"Le client {order.client.username} a annulé la commande pour "
            f"le service « {order.service_title_snapshot} ».\n\n"
            f"Voir la commande : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    elif new_status == "client_marked_complete":
        subject = f"[{site_name}] Le client a marqué la commande comme terminée"
        body = (
            f"Bonjour {provider.username},\n\n"
            f"Le client {order.client.username} a marqué la commande pour "
            f"« {order.service_title_snapshot} » comme terminée.\n\n"
            f"Validez pour finaliser : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    elif new_status == "completed":
        subject = f"[{site_name}] Une commande est terminée ✅"
        body = (
            f"Bonjour {provider.username},\n\n"
            f"La commande pour le service « {order.service_title_snapshot} » est maintenant "
            f"marquée comme terminée.\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )
    else:
        body = (
            f"Bonjour {provider.username},\n\n"
            f"Le statut d'une commande pour « {order.service_title_snapshot} » "
            f"a été mis à jour ({new_status}).\n\n"
            f"Voir la commande : {order_url}\n\n"
            f"Cordialement,\nL'équipe {site_name}"
        )

    _send_simple_email(provider.email, subject, body)


# -------------------------------------------------------------------
#  NOTIFICATIONS : ALERTES & FOLLOWERS (BOUCLES)
# -------------------------------------------------------------------

def notify_users_for_new_service_matching_alerts(service: ServiceOffer):
    """
    Quand un nouveau service est créé, notifie les utilisateurs ayant une alerte.
    """
    alerts = ServiceSearchAlert.objects.filter(is_active=True).select_related("user", "category")

    if not alerts.exists():
        return

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    service_url = f"{base_url}/services/{service.slug}/"

    for alert in alerts:
        user = alert.user
        if not user or not user.is_active:
            continue

        matches = True

        # 🔎 1) Mot-clé
        if alert.q:
            q = alert.q.strip().lower()
            haystack = " ".join([
                service.title or "",
                service.short_description or "",
                service.description or ""
            ]).lower()
            if q not in haystack:
                matches = False

        # 🔎 2) Catégorie
        if matches and alert.category:
            if service.category_id != alert.category_id:
                matches = False

        # 🔎 3) Prix min / max
        if matches and alert.min_price is not None:
            if service.price_min is not None and service.price_min < alert.min_price:
                matches = False
        if matches and alert.max_price is not None:
            if service.price_max is not None and service.price_max > alert.max_price:
                matches = False

        # 🔎 4) Ville
        if matches and alert.provider_city:
            profile = getattr(service.provider, "profile", None)
            city = getattr(profile, "city", "") if profile else ""
            if alert.provider_city.lower() not in (city or "").lower():
                matches = False

        if not matches:
            continue

        message_text = (
            f"Bonjour {user.username},\n\n"
            f"Un nouveau service correspond à votre recherche :\n"
            f"- Service : {service.title}\n"
            f"- Prestataire : {service.provider.username}\n"
            f"- Prix : {service.price_min} – {service.price_max} {service.currency}\n\n"
            f"Voir le service :\n"
            f"{service_url}\n\n"
            f"Cordialement,\n"
            f"L'équipe CampusHub"
        )

        # 🔔 Notification interne
        Notification.objects.create(
            user=user,
            notif_type="general",
            message=f"Nouveau service correspondant à votre recherche : {service.title}",
            offer=None,
            application=None,
        )

        # 📧 Email (Via Threading pour ne pas bloquer la boucle)
        if user.email:
            subject = f"Nouveau service correspondant à votre recherche : {service.title}"
            EmailThread(
                subject=subject,
                message=message_text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=True
            ).start()


def notify_clients_service_deactivated(service, clients):
    """
    Envoie un email aux clients (Async) pour les prévenir qu'un service a été désactivé.
    """
    subject = f"Service désactivé : {service.title}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    for user in clients:
        if not getattr(user, "email", None):
            continue

        message = (
            f"Bonjour {user.username},\n\n"
            f"Le service « {service.title} » proposé par {service.provider.username} "
            "a été désactivé par le prestataire.\n\n"
            "Les commandes déjà passées restent visibles dans votre historique, "
            "mais il n'est plus possible de passer de nouvelles commandes sur ce service.\n\n"
            "Merci d'utiliser CampusHub."
        )

        # Envoi via Threading
        EmailThread(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=True
        ).start()


def notify_followers_new_service(service):
    """
    Notifie les abonnés (Followers) d'un nouveau service (Async).
    """
    provider = service.provider
    followers = ProviderFollow.objects.select_related("client").filter(provider=provider)

    if not followers.exists():
        return

    service_url = _build_absolute_url(
        reverse("service_detail", kwargs={"slug": service.slug})
    )

    subject = f"Nouveau service de {provider.username} sur CampusHub"
    message_template = (
        "Bonjour {username},\n\n"
        "Le prestataire que tu suis, {provider_name}, vient de publier un nouveau service :\n"
        "« {service_title} ».\n\n"
        "Tu peux le découvrir ici : {url}\n\n"
        "— L'équipe CampusHub"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@campushub.local")

    for follow in followers:
        client = follow.client
        if not client.email:
            continue

        msg = message_template.format(
            username=client.username,
            provider_name=getattr(provider, "username", "un prestataire"),
            service_title=service.title,
            url=service_url,
        )
        
        # Envoi via Threading
        EmailThread(
            subject=subject,
            message=msg,
            from_email=from_email,
            recipient_list=[client.email],
            fail_silently=True
        ).start()


def notify_followers_new_package(service, package):
    """
    Notifie les abonnés d'un nouveau pack (Async).
    """
    provider = service.provider
    followers = ProviderFollow.objects.select_related("client").filter(provider=provider)

    if not followers.exists():
        return

    service_url = _build_absolute_url(
        reverse("service_detail", kwargs={"slug": service.slug})
    )

    subject = f"Nouveau pack sur le service « {service.title} »"
    message_template = (
        "Bonjour {username},\n\n"
        "{provider_name} vient d'ajouter un nouveau pack sur son service :\n"
        "« {service_title} ».\n\n"
        "Pack : {pack_title}\n"
        "Prix : {pack_price} {currency}\n\n"
        "Découvre les détails ici : {url}\n\n"
        "— L'équipe CampusHub"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@campushub.local")

    for follow in followers:
        client = follow.client
        if not client.email:
            continue

        msg = message_template.format(
            username=client.username,
            provider_name=getattr(provider, "username", "un prestataire"),
            service_title=service.title,
            pack_title=package.title,
            pack_price=package.price,
            currency=service.currency,
            url=service_url,
        )
        
        # Envoi via Threading
        EmailThread(
            subject=subject,
            message=msg,
            from_email=from_email,
            recipient_list=[client.email],
            fail_silently=True
        ).start()