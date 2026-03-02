# services/utils_score.py

from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import Profile
from .models import ProviderPenaltyLog


MAX_TRUST = 100
MIN_TRUST = 0


def _get_profile(user):
    """
    Renvoie le profil d'un user, ou None.
    """
    if not user or not getattr(user, "id", None):
        return None
    return getattr(user, "profile", None)


def _apply_trust_delta(user, delta, reason=""):
    """
    Applique un delta (positif ou négatif) au trust_score
    et crée un ProviderPenaltyLog cohérent.

    - delta > 0  → bonus (on ajoute des points)
    - delta < 0  → pénalité (on retire des points)
    """
    profile = _get_profile(user)
    if not profile:
        return

    old_score = profile.trust_score or 0

    # borne entre MIN_TRUST et MAX_TRUST
    new_score = max(MIN_TRUST, min(MAX_TRUST, old_score + delta))

    profile.trust_score = new_score
    profile.last_trust_update = timezone.now()
    profile.save(update_fields=["trust_score", "last_trust_update"])

    ProviderPenaltyLog.objects.create(
        provider=user,
        amount=delta,  # positif = bonus ; négatif = pénalité
        reason=reason or "Ajustement de score sans raison précisée",
    )


def decrease_trust_score(user, amount, reason=""):
    """
    Diminue le trust_score du prestataire (pénalité).

    amount = points à RETIRER (ex: 10, 20) → sera converti en delta négatif.
    """
    delta = -abs(amount)  # on force un nombre négatif
    _apply_trust_delta(user, delta, reason or "Pénalité sans raison précisée")


def increase_trust_score(user, amount, reason=""):
    """
    Augmente le trust_score du prestataire (bonus).

    amount = points à AJOUTER (ex: 5, 10) → sera converti en delta positif.
    """
    delta = abs(amount)  # on force un nombre positif
    _apply_trust_delta(user, delta, reason or "Augmentation du score")


def heal_trust_scores(days_without_penalty=7, heal_points=30):
    """
    Augmente légèrement le trust_score des prestataires qui
    n'ont pas eu de pénalité récente.

    À appeler périodiquement (cron / management command).
    - days_without_penalty : nombre de jours sans pénalité
    - heal_points : points rendus (bonus)
    """
    User = get_user_model()

    limit_date = timezone.now() - timedelta(days=days_without_penalty)

    # Prestataires qui ont un profil et un trust_score < MAX_TRUST
    qs = User.objects.filter(
        profile__isnull=False,
        profile__trust_score__lt=MAX_TRUST,
    )

    for user in qs:
        # pénalité récente ? (amount < 0 = pénalité)
        recent_penalty = ProviderPenaltyLog.objects.filter(
            provider=user,
            created_at__gte=limit_date,
            amount__lt=0,  # on regarde bien les pénalités (négatives)
        ).exists()

        if recent_penalty:
            continue

        # Pas de pénalité récente → on remonte un peu le score
        increase_trust_score(
            user,
            heal_points,
            "Restauration progressive du score (bonne conduite)",
        )