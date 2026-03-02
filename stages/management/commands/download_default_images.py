from django.core.management.base import BaseCommand
from django.conf import settings
from stages.models import StageOffer, OfferImage
import os, random

class Command(BaseCommand):
    help = "Ajoute jusqu’à 3 images par défaut à chaque offre selon son type (stage, emploi, alternance)."

    def handle(self, *args, **options):
        base_dir = os.path.join(settings.MEDIA_ROOT, "default_images")

        # Chaque type d'offre a son dossier dédié :
        image_pools = {
            "stage": os.path.join(base_dir, "stage"),
            "emploi": os.path.join(base_dir, "emploi"),
            "alternance": os.path.join(base_dir, "alternance"),
        }

        created = 0

        for offer in StageOffer.objects.all():
            if not offer.images.exists():
                offer_type = (offer.contract_type or "stage").lower()
                folder = image_pools.get(offer_type, image_pools["stage"])

                if os.path.exists(folder):
                    all_images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
                    random.shuffle(all_images)

                    # On choisit jusqu’à 3 images aléatoires :
                    for img_name in all_images[:3]:
                        image_path = f"default_images/{offer_type}/{img_name}"
                        OfferImage.objects.create(
                            offer=offer,
                            file=image_path,
                            caption=f"Image par défaut ({offer_type.capitalize()})"
                        )
                        created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} images ajoutées à {StageOffer.objects.count()} offres."))