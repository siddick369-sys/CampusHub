# services/management/commands/seed_service_tags.py

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from services.models import ServiceCategory, ServiceTag


CATEGORY_TAGS = {
    # Les clés doivent être les slugs de tes catégories (slugify du name)

    "menage-a-domicile": [
        "ménage",
        "repassage",
        "lessive",
        "nettoyage maison",
        "aide ménagère",
    ],
    "nettoyage-professionnel": [
        "nettoyage bureaux",
        "nettoyage magasin",
        "nettoyage après chantier",
        "entretien locaux",
    ],
    "jardinage-espaces-verts": [
        "jardinage",
        "tonte pelouse",
        "taille haies",
        "entretien jardin",
    ],

    "coiffure-tresses": [
        "coiffure femme",
        "coiffure homme",
        "tresses",
        "nattes",
        "locks",
    ],
    "esthetique-maquillage": [
        "maquillage",
        "manucure",
        "pedicure",
        "soins visage",
    ],
    "massage-bien-etre": [
        "massage",
        "relaxation",
        "bien-être",
    ],

    "cuisine-a-domicile": [
        "repas maison",
        "cuisine africaine",
        "plats à domicile",
    ],
    "traiteur-evenements": [
        "traiteur",
        "buffet",
        "mariage",
        "anniversaire",
    ],
    "patisserie-boulangerie": [
        "gâteaux",
        "pâtisserie",
        "desserts",
    ],

    "babysitting-garde-denfants": [
        "babysitting",
        "garde enfants",
        "aide scolaire",
    ],
    "aide-a-domicile-assistance": [
        "aide personnes âgées",
        "assistance domicile",
    ],

    "plomberie": [
        "fuite",
        "installation sanitaire",
        "dépannage plomberie",
    ],
    "electricite": [
        "installation électrique",
        "dépannage électrique",
        "prise",
        "interrupteur",
    ],
    "reparation-electromenager": [
        "frigo",
        "gazinière",
        "ventilateur",
        "machine à laver",
    ],
    "reparation-telephones-pc": [
        "réparation smartphone",
        "réparation pc",
        "changement écran",
    ],
    "bricolage-petits-travaux": [
        "montage meuble",
        "petits travaux",
    ],
    "maconnerie-construction": [
        "maçonnerie",
        "carrelage",
        "construction",
    ],
    "peinture-decoration": [
        "peinture intérieure",
        "peinture extérieure",
        "décoration",
    ],
    "menuiserie-serrurerie": [
        "menuiserie",
        "serrurerie",
        "porte",
        "fenêtre",
    ],

    "developpement-web": [
        "site vitrine",
        "e-commerce",
        "frontend",
        "backend",
    ],
    "developpement-mobile": [
        "application android",
        "application mobile",
    ],
    "graphisme-design": [
        "logo",
        "flyer",
        "carte de visite",
        "bannière",
    ],
    "montage-video-animation": [
        "montage vidéo",
        "motion design",
        "sous-titrage",
    ],
    "community-management": [
        "facebook",
        "instagram",
        "tiktok",
        "réseaux sociaux",
    ],
    "installation-assistance-informatique": [
        "installation windows",
        "antivirus",
        "bureautique",
    ],

    "photographie": [
        "shooting",
        "photo événement",
        "reportage photo",
    ],
    "videographie-production": [
        "tournage",
        "clip vidéo",
        "captation",
    ],
    "dj-sonorisation": [
        "dj",
        "sono",
        "animation musicale",
    ],
    "organisation-devenements": [
        "wedding planner",
        "organisation mariage",
        "événementiel",
    ],

    "cours-particuliers-soutien-scolaire": [
        "maths",
        "physique",
        "français",
        "soutien scolaire",
    ],
    "cours-universitaires-prepa-concours": [
        "prépa concours",
        "aide universitaire",
    ],
    "cours-de-langues": [
        "anglais",
        "français",
        "allemand",
    ],
    "formation-informatique": [
        "excel",
        "word",
        "programmation",
    ],

    "redaction-correction": [
        "rédaction cv",
        "lettre de motivation",
        "correction texte",
    ],
    "traduction": [
        "traduction français-anglais",
        "traduction documents",
    ],
    "comptabilite-gestion": [
        "tenue de comptes",
        "comptabilité",
    ],
    "conseil-coaching": [
        "coaching",
        "orientation",
        "accompagnement",
    ],
    "assistance-administrative": [
        "démarches administratives",
        "formulaires",
    ],

    "transport-chauffeur-prive": [
        "transport urbain",
        "chauffeur privé",
    ],
    "livraison-coursier": [
        "livraison repas",
        "livraison colis",
        "coursier",
    ],
    "demenagement": [
        "déménagement",
        "transport meubles",
    ],

    "toilettage-soins-animaux": [
        "toilettage chien",
        "toilettage chat",
    ],
    "garde-promenade-animaux": [
        "garde animaux",
        "promenade chien",
    ],

    "coaching-bien-etre-developpement-personnel": [
        "développement personnel",
        "gestion stress",
        "motivation",
    ],
    "sport-coaching-sportif": [
        "coach sportif",
        "fitness",
        "remise en forme",
    ],

    "art-artisanat": [
        "artisanat",
        "création objets",
        "décoration",
    ],
    "animation-loisirs": [
        "animation enfants",
        "atelier créatif",
    ],
}


class Command(BaseCommand):
    help = "Crée des tags de services par défaut et les associe aux catégories."

    def handle(self, *args, **options):
        created_tags = 0
        linked_tags = 0

        for cat_slug, tag_names in CATEGORY_TAGS.items():
            try:
                category = ServiceCategory.objects.get(slug=cat_slug)
            except ServiceCategory.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Catégorie introuvable pour le slug: {cat_slug}"))
                continue

            for name in tag_names:
                tag_slug = slugify(name)
                tag, created = ServiceTag.objects.get_or_create(
                    slug=tag_slug,
                    defaults={"name": name},
                )
                if created:
                    created_tags += 1
                    self.stdout.write(self.style.SUCCESS(f"Tag créé: {name}"))

                category.default_tags.add(tag)
                linked_tags += 1

            self.stdout.write(self.style.SUCCESS(
                f"Catégorie '{category.name}': {len(tag_names)} tags liés."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Terminé. {created_tags} tag(s) créé(s), {linked_tags} liaison(s) catégorie-tag effectuée(s)."
        ))