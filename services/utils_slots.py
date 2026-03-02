# services/utils_slots.py
from datetime import datetime, timedelta, time

from django.utils import timezone

from .models import ProviderWeeklySlot, ProviderVacation, ServiceOrder

ACTIVE_STATUSES = ("pending", "accepted", "in_progress")  # adapte si besoin


def is_on_vacation(provider, date):
    """
    True si 'date' tombe dans une période de vacances du prestataire.
    """
    return ProviderVacation.objects.filter(
        provider=provider,
        start_date__lte=date,
        end_date__gte=date
    ).exists()


def generate_time_range(start_time, end_time, step_minutes):
    """
    Génère des (start, end) datetime.time en pas de 'step_minutes'.
    """
    current = datetime.combine(datetime.today().date(), start_time)
    end_dt = datetime.combine(datetime.today().date(), end_time)
    delta = timedelta(minutes=step_minutes)

    while current + delta <= end_dt:
        yield (current.time(), (current + delta).time())
        current += delta


def get_service_slots_for_date(service, date):
    """
    Retourne une liste de créneaux possibles pour un service donné à une date donnée.

    Chaque item est un dict :
    {
      "start_time": datetime.time,
      "end_time": datetime.time,
      "capacity": int,
      "used": int,
      "remaining": int,
      "is_full": bool,
    }
    """
    provider = service.provider
    profile = getattr(provider, "profile", None)

    # indisponibilité globale / vacances
    if profile and not profile.provider_is_available:
        return []

    if profile and profile.provider_unavailable_until and profile.provider_unavailable_until >= date:
        return []

    if is_on_vacation(provider, date):
        return []

    weekday = date.weekday()  # 0 = lundi

    # Créneaux spécifiques à ce service
    specific_slots = ProviderWeeklySlot.objects.filter(
        provider=provider,
        weekday=weekday,
        is_active=True,
        service=service,
    )

    # Créneaux génériques (sans service)
    generic_slots = ProviderWeeklySlot.objects.filter(
        provider=provider,
        weekday=weekday,
        is_active=True,
        service__isnull=True,
    )

    slots_qs = list(specific_slots) or list(generic_slots)
    if not slots_qs:
        return []

    slot_duration = service.slot_duration_minutes or 60
    result = []

    for weekly in slots_qs:
        # On découpe le créneau en sous-créneaux de slot_duration
        for start_t, end_t in generate_time_range(
            weekly.start_time, weekly.end_time, slot_duration
        ):
            # Construire des datetime pour interroger les commandes
            start_dt = datetime.combine(date, start_t)
            end_dt = datetime.combine(date, end_t)
            start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
            end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())

            # Combien de commandes chevauchent ce créneau ?
            used_count = ServiceOrder.objects.filter(
                service=service,
                status__in=ACTIVE_STATUSES,
                appointment_start__lt=end_dt,
                appointment_end__gt=start_dt,
            ).count()

            capacity = weekly.max_parallel_orders or 1
            # On peut aussi limiter par service.slot_max_clients
            capacity = min(capacity, service.slot_max_clients or capacity)

            remaining = max(capacity - used_count, 0)

            result.append({
                "start_time": start_t,
                "end_time": end_t,
                "capacity": capacity,
                "used": used_count,
                "remaining": remaining,
                "is_full": remaining <= 0,
            })

    # On peut filtrer pour ne renvoyer que les créneaux où remaining > 0
    return [s for s in result if not s["is_full"]]