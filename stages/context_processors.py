# stages/context_processors.py
from django.utils import timezone

from stages.models import StageOffer, Application, StudentDocument
from orientation.models import OrientationResult


def student_todo_badge(request):
    """
    Ajoute au contexte global : student_todo_count
    (nombre de points dans 'À faire aujourd'hui' pour l'étudiant).
    """
    user = request.user

    # Pas connecté → rien
    if not user.is_authenticated:
        return {}

    profile = getattr(user, "profile", None)
    if not profile or profile.role != "student":
        return {}

    today = timezone.now().date()
    tomorrow = today + timezone.timedelta(days=1)

    todo_count = 0

    # 1) A-t-il un CV par défaut ?
    has_default_cv = StudentDocument.objects.filter(
        user=user,
        doc_type="cv",
        is_default_cv=True
    ).exists()

    if not has_default_cv:
        todo_count += 1  # "Tu n’as pas encore de CV généré"

    # 2) Dernière candidature
    last_application = (
        Application.objects
        .filter(student=user)
        .order_by("-created_at")
        .first()
    )

    if last_application:
        delta = timezone.now() - last_application.created_at
        days = delta.days
        if days >= 7:
            todo_count += 1  # "Tu n’as pas postulé depuis X jours"
    else:
        # Jamais postulé → on compte aussi
        todo_count += 1

    # 3) Offre qui correspond au profil et se termine demain
    last_orientation = (
        OrientationResult.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    if last_orientation:
        suggested_tracks = last_orientation.suggested_tracks.all()
        if suggested_tracks.exists():
            matching_offers_ending_tomorrow = (
                StageOffer.objects
                .filter(
                    is_active=True,
                    status="published",
                    application_deadline=tomorrow,
                    related_tracks__in=suggested_tracks,
                )
                .distinct()
            )
            if matching_offers_ending_tomorrow.exists():
                todo_count += 1  # "Une offre se termine demain"

    return {
        "student_todo_count": todo_count
    }
    
from .models import Conversation, Message
from django.db.models import Q

def messaging_counts(request):
    """
    Ajoute le nombre de messages non lus dans le contexte global.
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user

    conv_ids = Conversation.objects.filter(
        Q(student=user) | Q(company=user),
        is_active=True
    ).values_list("id", flat=True)

    unread_count = Message.objects.filter(
        conversation_id__in=conv_ids
    ).exclude(sender=user).filter(is_read=False).count()

    return {
        "unread_messages_count": unread_count
    }
    
from django.conf import settings

def websocket_settings(request):
    """
    Injecte les infos WebSocket dans tous les templates.
    """
    return {
        "CALL_WS_SCHEME": getattr(settings, "CALL_WS_SCHEME", "ws"),
        "CALL_WS_HOST": getattr(settings, "CALL_WS_HOST", "127.0.0.1"),
        "CALL_WS_PORT": getattr(settings, "CALL_WS_PORT", "8001"),
    }