# services/utils_availability.py

from django.utils import timezone

def get_provider_availability_status(user):
    """
    Retourne un tuple (code, label) :

    - ("available_now", "Disponible aujourd’hui")
    - ("unavailable_until", "Indisponible jusqu’au JJ/MM/AAAA")
    - ("unavailable", "Indisponible pour le moment")
    - (None, None) si pas un prestataire
    """
    profile = getattr(user, "profile", None)
    if not profile or profile.role != "provider" or not profile.is_service_provider:
        return (None, None)

    today = timezone.now().date()

    # Cas indisponible prolongé
    if profile.provider_unavailable_until and profile.provider_unavailable_until >= today:
        date_str = profile.provider_unavailable_until.strftime("%d/%m/%Y")
        return ("unavailable_until", f"Indisponible jusqu’au {date_str}")

    # Cas switch global OFF
    if not profile.provider_is_available:
        return ("unavailable", "Indisponible pour le moment")

    # Sinon, c’est ok
    return ("available_now", "Disponible aujourd’hui")