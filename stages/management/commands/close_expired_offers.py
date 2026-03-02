from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, F

from stages.models import StageOffer
from stages.views import notify_company_offer_closed


class Command(BaseCommand):
    help = "Ferme les offres expirées (date limite ou max candidatures) et notifie les entreprises."

    def handle(self, *args, **options):
        today = timezone.now().date()

        # Offres dont la date limite est passée
        deadline_q = Q(application_deadline__isnull=False, application_deadline__lt=today)

        # Offres ayant atteint le max de candidatures
        max_apps_q = Q(max_applicants__isnull=False, applications_count__gte=F('max_applicants'))

        # On cible seulement les offres encore actives
        queryset = StageOffer.objects.filter(
            is_active=True
        ).filter(
            deadline_q | max_apps_q
        )

        count = queryset.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("Aucune offre à clôturer."))
            return

        self.stdout.write(self.style.WARNING(f"{count} offre(s) expirée(s) trouvée(s)."))

        for offer in queryset:
            # Déterminer la raison principale
            max_reached = (
                offer.max_applicants is not None
                and offer.applications_count >= offer.max_applicants
            )
            deadline_passed = (
                offer.application_deadline is not None
                and offer.application_deadline < today
            )

            if max_reached and deadline_passed:
                reason = "both"
            elif max_reached:
                reason = "max_applicants"
            elif deadline_passed:
                reason = "deadline"
            else:
                reason = "unknown"

            # Fermer l'offre
            offer.is_active = False
            if getattr(offer, 'status', None) == 'published':
                offer.status = 'archived'
            offer.save(update_fields=['is_active', 'status'])

            # Notification + email à l'entreprise
            notify_company_offer_closed(offer, reason)

            self.stdout.write(self.style.SUCCESS(
                f"Offre clôturée : {offer.title} (raison: {reason})"
            ))

        self.stdout.write(self.style.SUCCESS(f"Total offres clôturées : {count}"))