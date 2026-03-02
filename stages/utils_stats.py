# stages/utils_stats.py
from datetime import timedelta

from django.utils import timezone

from .models import Application, StageOffer

# stages/utils_stats.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, F, ExpressionWrapper, DurationField

from .models import Application, StageOffer

def get_offer_stats(offer: StageOffer):
    """
    Calcule les stats pour une offre de manière optimisée (SQL).
    """
    # 1) Toutes les candidatures pour cette offre
    qs = offer.applications.all()
    total_applications = qs.count()

    # 2) Temps moyen de réponse (calculé directement en DB)
    # On filtre les status 'submitted' et ceux sans date de changement
    stats = qs.exclude(status='submitted') \
              .exclude(status_changed_at__isnull=True) \
              .aggregate(
                  avg_diff=Avg(
                      ExpressionWrapper(
                          F('status_changed_at') - F('created_at'),
                          output_field=DurationField()
                      )
                  )
              )

    avg_response_days = None
    # stats['avg_diff'] est un timedelta ou None
    if stats['avg_diff']:
        # total_seconds() convertit le timedelta en secondes
        avg_days = stats['avg_diff'].total_seconds() / 86400  # 86400s = 1 jour
        avg_response_days = round(avg_days, 1)

    # 3) Nombre d'étudiants acceptés par cette entreprise (toutes offres confondues)
    company_accepted_students_count = (
        Application.objects
        .filter(
            offer__company=offer.company,
            status='accepted',
        )
        .values('student')
        .distinct()
        .count()
    )

    return {
        "total_applications": total_applications,
        "avg_response_days": avg_response_days,
        "company_accepted_students_count": company_accepted_students_count,
    }

# (Laissez votre fonction get_company_rating_stats ici si elle existe dans le fichier d'origine)
from django.db.models import Avg
from .models import StageReview

def get_company_rating_stats(company):
    """
    Retourne :
      - avg_rating: moyenne sur 5
      - reviews_count: nombre d'avis publics
    """
    qs = StageReview.objects.filter(
        company=company,
        is_public=True,
    )

    stats = qs.aggregate(avg_rating=Avg("rating"))
    avg_rating = stats["avg_rating"]

    if avg_rating is not None:
        avg_rating = round(avg_rating, 1)

    return {
        "avg_rating": avg_rating,
        "reviews_count": qs.count(),
    }