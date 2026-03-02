# services/management/commands/heal_trust.py

from django.core.management.base import BaseCommand
from services.utils_scores import heal_trust_scores

class Command(BaseCommand):
    help = "Restaure légèrement le trust_score des prestataires sans pénalité récente."

    def handle(self, *args, **options):
        heal_trust_scores()
        self.stdout.write(self.style.SUCCESS("Trust scores mis à jour."))