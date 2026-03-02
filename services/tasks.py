# services/tasks.py

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .utils_scores import decrease_trust_score

from .models import ServiceOrder# ou recopie la liste

ACTIVE_STATUSES = ["pending", "accepted", "in_progress"]
ALERT_WINDOW_HOURS = 24


@shared_task(name="services.tasks.expire_old_service_orders")
def expire_old_service_orders():
    """
    Tâche périodique qui marque les commandes dont la date limite est dépassée
    comme 'expired'.
    """
    now = timezone.now()
    qs = ServiceOrder.objects.filter(
        status__in=ACTIVE_STATUSES,
        due_date__lt=now,
    )
    updated = qs.update(status="expired", status_changed_at=now)
    
    decrease_trust_score(qs.provider, 10, "commande expirée sans action du prestataire")
    
    return updated


from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import FavoriteService, ServiceOrder

ACTIVE_STATUSES = ["pending", "accepted", "in_progress"]
ALERT_WINDOW_HOURS = 24



@shared_task(name="services.tasks.notify_favorite_services_nearly_expired")
def notify_favorite_services_nearly_expired():
    """
    Tâche périodique :
      - recherche les commandes actives dont la due_date est dans < 24h
      - trouve les services mis en favoris par des utilisateurs
      - envoie un email (une seule fois par jour max par favori)
    """
    now = timezone.now()
    soon = now + timedelta(hours=ALERT_WINDOW_HOURS)

    # 1) Commandes proches de l'échéance
    orders = (
        ServiceOrder.objects
        .filter(
            status__in=ACTIVE_STATUSES,
            due_date__gte=now,
            due_date__lte=soon,
        )
        .select_related("service")
    )

    service_ids = {o.service_id for o in orders}
    order_by_service = {}
    for o in orders:
        order_by_service.setdefault(o.service_id, []).append(o)

    if not service_ids:
        return 0

    # 2) Favoris correspondant à ces services
    favorites = (
        FavoriteService.objects
        .filter(service_id__in=service_ids, user__is_active=True)
        .select_related("user", "service")
    )

    sent_count = 0

    for fav in favorites:
        # Evite de spammer : on ne notifie pas si déjà notifié dans les dernières 24h
        if fav.last_notified_at and fav.last_notified_at > (now - timedelta(hours=ALERT_WINDOW_HOURS)):
            continue

        # On prend la commande la plus proche
        related_orders = order_by_service.get(fav.service_id, [])
        if not related_orders:
            continue

        order = sorted(related_orders, key=lambda o: o.due_date)[0]

        send_favorite_service_expiring_email(fav, order)
        fav.last_notified_at = now
        fav.save(update_fields=["last_notified_at"])
        sent_count += 1

    return sent_count


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

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, max_retries=3)
def send_plain_email_service_task(self, subject, message, from_email, recipient_list):
    try:
        send_mail(
            subject,
            message,
            from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_html_email_service_task(self, subject, message, from_email, recipient_list, html_message=None):
    try:
        send_mail(
            subject,
            message,
            from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)