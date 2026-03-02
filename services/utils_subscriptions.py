# services/utils_subscriptions.py
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth import get_user_model

from accounts.models import SubscriptionPlan, Subscription
from .models import ServiceOffer, ServiceOrder

User = get_user_model()

def get_default_plan():
    """
    Retourne le plan 'par défaut' pour les prestataires.
    """
    plan = SubscriptionPlan.objects.filter(role_target='provider', is_default=True, is_active=True).first()
    if plan:
        return plan

    # Faux plan en mémoire, NON sauvegardé si rien en base
    class DummyPlan:
        code = "FREE"
        name = "Gratuit"
        price = 0
        currency = "FCFA"
        max_active_services = 1
        max_featured_services = 0
        max_urgent_orders_per_day = 0
        max_time_slots = 10
        has_analytics = False

    return DummyPlan()

from services.models import ProviderTimeSlot

def get_provider_slot_usage(user):
    """
    Retourne le nombre total de créneaux créés par le prestataire.
    """
    if not user or not getattr(user, "id", None):
        return 0

    return ProviderTimeSlot.objects.filter(provider=user).count()


def can_create_new_slot(user):
    """
    Vérifie si l'utilisateur peut encore créer un nouveau créneau.
    """
    plan = get_provider_current_plan(user)
    used_slots = get_provider_slot_usage(user)

    return used_slots < plan.max_time_slots


def get_provider_current_plan(user):
    """
    Retourne le plan courant pour un prestataire donné via accounts.Subscription.
    """
    if not user or not getattr(user, "id", None):
        return get_default_plan()

    sub = Subscription.objects.filter(
        user=user,
        is_active=True
    ).select_related('plan').first()

    if sub and sub.plan and sub.plan.role_target == 'provider':
        if sub.is_expired:
            return get_default_plan()
        return sub.plan

    return get_default_plan()


def get_provider_service_usage(user):
    """
    Retourne quelques stats sur l'utilisation du plan par le prestataire.
    """
    if not user or not getattr(user, "id", None):
        return {"active_services": 0, "featured_services": 0}

    qs = ServiceOffer.objects.filter(
        provider=user,
        status="active",
        visibility="public",
    )
    active_count = qs.count()
    featured_count = qs.filter(is_featured=True).count()

    return {
        "active_services": active_count,
        "featured_services": featured_count,
    }


def can_create_new_service(user):
    """
    True/False selon si le prestataire a encore le droit de créer un service actif.
    """
    plan = get_provider_current_plan(user)
    usage = get_provider_service_usage(user)

    return usage["active_services"] < plan.max_services_active


def can_set_service_featured(user):
    """
    True/False selon si le prestataire peut encore mettre un service en 'mis en avant'.
    """
    plan = get_provider_current_plan(user)
    usage = get_provider_service_usage(user)

    return usage["featured_services"] < plan.max_featured_services


def can_create_urgent_order_for_service(service):
    """
    Vérifie si le quota urgent/jour pour ce service et ce plan est OK.
    """
    provider = service.provider
    plan = get_provider_current_plan(provider)

    if plan.max_urgent_orders_per_day <= 0:
        return False

    today = timezone.now().date()
    urgent_today = ServiceOrder.objects.filter(
        service=service,
        is_urgent=True,
        created_at__date=today,
    ).count()

    return urgent_today < plan.max_urgent_orders_per_day

def send_subscription_changed_email(provider, old_plan, new_plan):
    """
    Raccourci pour envoyer l'email de changement d'abonnement.
    """
    from .utils_emails import send_subscription_changed_email as send_email
    send_email(provider, old_plan, new_plan)
