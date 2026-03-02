from django.utils import timezone
from django.db.models import Q, Count, Avg

from stages.models import Application, StageReview, Conversation, Message
from accounts.models import Profile


BASE_TRUST = 50
MAX_TRUST = 100
MIN_TRUST = 0


def recompute_trust_score_for_profile(profile: Profile) -> int:
    """
    Calcule un trust_score (0–100) pour un profil étudiant.
    Tu peux adapter pour les entreprises si tu veux plus tard.
    """
    user = profile.user
    score = BASE_TRUST

    # On se concentre surtout sur les étudiants
    if profile.role != "student":
        profile.trust_score = score
        profile.last_trust_update = timezone.now()
        profile.save(update_fields=["trust_score", "last_trust_update"])
        return score

    # 1️⃣ Candidatures acceptées → + points
    accepted_apps = Application.objects.filter(
        student=user,
        status="accepted",
    ).count()

    # max +20 points
    score += min(accepted_apps * 2, 20)

    # 2️⃣ Reviews laissées par les entreprises sur l'étudiant (si tu en as)
    # Ici on suppose que StageReview a un champ "rating" (1–5) et
    # "student" et "company".
    reviews_stats = (
        StageReview.objects
        .filter(student=user)
        .aggregate(avg_rating=Avg("rating"), count=Count("id"))
    )
    avg_rating = reviews_stats["avg_rating"] or 0
    review_count = reviews_stats["count"] or 0

    if review_count >= 3 and avg_rating >= 4:
        # +10 si globalement très bon
        score += 10
    elif review_count >= 3 and avg_rating < 3:
        # -10 si beaucoup d'avis mais mauvais
        score -= 10

    # 3️⃣ Mutes / strikes en messagerie → - points
    convs = Conversation.objects.filter(student=user)
    total_strikes = 0
    muted_times = 0

    now = timezone.now()
    for conv in convs:
        total_strikes += conv.student_strike_count or 0
        if conv.student_muted_until and conv.student_muted_until > now:
            muted_times += 1

    # -2 points par strike (max -20)
    score -= min(total_strikes * 2, 20)

    # -5 par conversation où l'étudiant est actuellement mute (max -15)
    score -= min(muted_times * 5, 15)

    # 4️⃣ Signalements / abus (si tu as un modèle ConversationReport)
    # Exemple : ConversationReport avec fields reporter, reported_user, is_valid
    try:
        from stages.models import ConversationReport
        reports_count = ConversationReport.objects.filter(
            reported_user=user,
            # éventuellement seulement ceux validés par un admin
            # is_valid=True
        ).count()
        # -5 par report (max -25)
        score -= min(reports_count * 5, 25)
    except Exception:
        # si tu n'as pas encore ce modèle, on ignore
        pass

    # 5️⃣ Taux de lecture des messages importants (entretien / rdv)
    important_messages = Message.objects.filter(
        conversation__student=user,
        sender__profile__role="company",
    ).filter(
        Q(text__icontains="entretien") |
        Q(text__icontains="interview") |
        Q(text__icontains="rdv") |
        Q(text__icontains="rendez-vous")
    )

    total_imp = important_messages.count()
    if total_imp >= 5:
        read_imp = important_messages.filter(is_read=True).count()
        ratio = read_imp / total_imp
        if ratio >= 0.8:
            score += 5
        elif ratio < 0.4:
            score -= 5

    # Clamp 0–100
    score = max(MIN_TRUST, min(MAX_TRUST, score))

    profile.trust_score = score
    profile.last_trust_update = timezone.now()
    profile.save(update_fields=["trust_score", "last_trust_update"])

    return score