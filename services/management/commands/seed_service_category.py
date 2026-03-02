# services/management/commands/seed_service_categories.py

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from services.models import ServiceCategory


CATEGORIES = [
    # 🧹 Maison & ménage
    {
        "name": "Ménage à domicile",
        "description": "Nettoyage de maison, appartement, repassage, lessive.",
    },
    {
        "name": "Nettoyage professionnel",
        "description": "Nettoyage de bureaux, magasins, locaux, nettoyage après chantier.",
    },
    {
        "name": "Jardinage & Espaces verts",
        "description": "Entretien de jardin, tonte, taille, arrosage, aménagement paysager.",
    },

    # 💇 Beauté & bien-être
    {
        "name": "Coiffure & Tresses",
        "description": "Coiffure femme, homme, enfants, tresses, locks, coiffure à domicile.",
    },
    {
        "name": "Esthétique & Maquillage",
        "description": "Maquillage professionnel, manucure, pédicure, soins du visage.",
    },
    {
        "name": "Massage & Bien-être",
        "description": "Massages à domicile, relaxation, soins corporels.",
    },

    # 🍲 Cuisine & alimentation
    {
        "name": "Cuisine à domicile",
        "description": "Préparation de repas à domicile, cuisine familiale, plats africains ou européens.",
    },
    {
        "name": "Traiteur & Événements",
        "description": "Traiteur pour mariages, anniversaires, événements d’entreprise.",
    },
    {
        "name": "Pâtisserie & Boulangerie",
        "description": "Gâteaux, pâtisseries, snacks, buffets sucrés.",
    },

    # 👶 Famille, enfants & aide à la personne
    {
        "name": "Babysitting & Garde d’enfants",
        "description": "Garde à domicile, accompagnement à l’école, surveillance occasionnelle.",
    },
    {
        "name": "Aide à domicile & Assistance",
        "description": "Aide aux personnes âgées, accompagnement, assistance quotidienne.",
    },

    # 🛠️ Réparation, artisans & bâtiment
    {
        "name": "Plomberie",
        "description": "Installation, dépannage, réparation de fuites, sanitaires.",
    },
    {
        "name": "Électricité",
        "description": "Installation électrique, réparation de pannes, luminaires.",
    },
    {
        "name": "Réparation électroménager",
        "description": "Réparation de frigos, gazinières, ventilateurs, etc.",
    },
    {
        "name": "Réparation téléphones & PC",
        "description": "Réparation smartphones, tablettes, ordinateurs, logiciels.",
    },
    {
        "name": "Bricolage & Petits travaux",
        "description": "Montage de meubles, travaux divers, petites réparations.",
    },
    {
        "name": "Maçonnerie & Construction",
        "description": "Gros œuvre, rénovation, maçonnerie, carrelage.",
    },
    {
        "name": "Peinture & Décoration",
        "description": "Peinture intérieure/extérieure, décoration, rafraîchissement de murs.",
    },
    {
        "name": "Menuiserie & Serrurerie",
        "description": "Portes, fenêtres, meubles sur mesure, dépannage serrurerie.",
    },

    # 📱 Digital, informatique & web
    {
        "name": "Développement Web",
        "description": "Sites vitrines, e-commerce, applications web.",
    },
    {
        "name": "Développement Mobile",
        "description": "Applications Android / iOS, prototypage, intégration.",
    },
    {
        "name": "Graphisme & Design",
        "description": "Logos, flyers, cartes de visite, bannières, maquettes.",
    },
    {
        "name": "Montage vidéo & Animation",
        "description": "Montage vidéo, motion design, sous-titrage.",
    },
    {
        "name": "Community Management",
        "description": "Gestion de pages Facebook, Instagram, TikTok, contenu social.",
    },
    {
        "name": "Installation & Assistance informatique",
        "description": "Installation de logiciels, systèmes, antivirus, configuration.",
    },

    # 📸 Média & Événementiel
    {
        "name": "Photographie",
        "description": "Shooting photo, événements, studio, portraits.",
    },
    {
        "name": "Vidéographie & Production",
        "description": "Tournage vidéo, clips, captation d’événements.",
    },
    {
        "name": "DJ & Sonorisation",
        "description": "Animation musicale, matériel de sonorisation, mix DJ.",
    },
    {
        "name": "Organisation d’événements",
        "description": "Wedding planner, organisation d’anniversaires, événements pro.",
    },

    # 📚 Éducation & formation
    {
        "name": "Cours particuliers & Soutien scolaire",
        "description": "Aide aux devoirs, soutien primaire, collège, lycée.",
    },
    {
        "name": "Cours universitaires & Prépa concours",
        "description": "Aide en math, informatique, économie, préparation aux examens.",
    },
    {
        "name": "Cours de langues",
        "description": "Cours d’anglais, français, allemand, etc.",
    },
    {
        "name": "Formation informatique",
        "description": "Bureautique, programmation, logiciels pro.",
    },

    # 🧾 Business, administratif & pro
    {
        "name": "Rédaction & Correction",
        "description": "CV, lettres de motivation, rapports, mémoires.",
    },
    {
        "name": "Traduction",
        "description": "Traduction de documents, localisation de contenu.",
    },
    {
        "name": "Comptabilité & Gestion",
        "description": "Tenue de comptes, déclarations, conseil financier de base.",
    },
    {
        "name": "Conseil & Coaching",
        "description": "Coaching personnel, coaching carrière, orientation pro.",
    },
    {
        "name": "Assistance administrative",
        "description": "Démarches, formulaires, organisation de documents.",
    },

    # 🚗 Transport & logistique
    {
        "name": "Transport & Chauffeur privé",
        "description": "Transport de personnes, chauffeur à la demande.",
    },
    {
        "name": "Livraison & Coursier",
        "description": "Livraison de colis, repas, documents.",
    },
    {
        "name": "Déménagement",
        "description": "Aide au déménagement, manutention, transport de meubles.",
    },

    # 🐾 Animaux
    {
        "name": "Toilettage & Soins animaux",
        "description": "Toilettage chiens/chats, soins de base.",
    },
    {
        "name": "Garde & Promenade d’animaux",
        "description": "Garde d’animaux à domicile, promenade de chiens.",
    },

    # 🧑‍⚕️ Bien-être & para-santé (soft, pas médical)
    {
        "name": "Coaching bien-être & développement personnel",
        "description": "Accompagnement mental, gestion du stress, motivation.",
    },
    {
        "name": "Sport & Coaching sportif",
        "description": "Coaching sportif, fitness, remise en forme.",
    },

    # 🎨 Art & loisirs
    {
        "name": "Art & Artisanat",
        "description": "Création d’objets, décoration, artisanat local.",
    },
    {
        "name": "Animation & Loisirs",
        "description": "Animation pour enfants, ateliers créatifs, loisirs.",
    },
]


class Command(BaseCommand):
    help = "Crée automatiquement une large liste de catégories de services par défaut."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for index, cat in enumerate(CATEGORIES, start=1):
            name = cat["name"]
            description = cat["description"]
            slug = slugify(name)

            obj, created = ServiceCategory.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    # Si ton modèle a d'autres champs, tu peux compléter ici :
                    # "is_active": True,
                    # "sort_order": index,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Créé : {name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Mis à jour : {name}"))

        self.stdout.write(self.style.SUCCESS(
            f"Terminé. {created_count} catégorie(s) créée(s), {updated_count} mise(s) à jour."
        ))