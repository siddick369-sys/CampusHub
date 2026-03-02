from django.core.management.base import BaseCommand
from incubation.models import Competence

class Command(BaseCommand):
    help = 'Remplit la base de données avec 50 compétences variées (Tech, Art, Business...)'

    def handle(self, *args, **kwargs):
        # Liste des compétences (Nom, Couleur Hex)
        competences_data = [
            # --- PÔLE TECH & DIGITAL (Bleu / Violet) ---
            ("Développement Python", "#3B82F6"),
            ("Développement Web (HTML/CSS/JS)", "#2563EB"),
            ("Intelligence Artificielle", "#8B5CF6"),
            ("Cybersécurité", "#6366F1"),
            ("Data Science", "#0EA5E9"),
            ("Réseaux & Télécoms", "#06B6D4"),
            ("Blockchain", "#A855F7"),
            ("DevOps & Cloud", "#4F46E5"),
            ("Maintenance Info", "#60A5FA"),
            ("Excel Avancé", "#22D3EE"),

            # --- PÔLE DESIGN & ART (Rose / Orange) ---
            ("Design UI/UX", "#EC4899"),
            ("Graphisme", "#F472B6"),
            ("Montage Vidéo", "#F97316"),
            ("Motion Design", "#FB923C"),
            ("Modélisation 3D", "#EF4444"),
            ("Photographie", "#FDA4AF"),
            ("Architecture d'intérieur", "#F87171"),
            ("Illustration", "#FB7185"),
            ("Sound Design", "#F43F5E"),
            ("Mode & Stylisme", "#E11D48"),

            # --- PÔLE BUSINESS (Vert / Or) ---
            ("Marketing Digital", "#10B981"),
            ("Community Management", "#34D399"),
            ("Stratégie SEO/SEA", "#059669"),
            ("Vente & Commerce", "#FBBF24"),
            ("Entrepreneuriat", "#D97706"),
            ("Comptabilité", "#F59E0B"),
            ("Finance", "#B45309"),
            ("Gestion de Projet", "#047857"),
            ("Ressources Humaines", "#065F46"),
            ("Droit des Affaires", "#65A30D"),

            # --- PÔLE INGÉNIERIE & MÉTIERS (Gris / Terre) ---
            ("Génie Civil & BTP", "#64748B"),
            ("Électronique", "#475569"),
            ("Électricité", "#94A3B8"),
            ("Mécanique", "#525252"),
            ("Topographie", "#78716C"),
            ("Logistique", "#57534E"),
            ("Énergies Renouvelables", "#84CC16"),
            ("Agronomie", "#4ADE80"),
            ("Chimie & Biologie", "#A3E635"),
            ("Qualité (QHSE)", "#3F6212"),

            # --- PÔLE SOFT SKILLS & LANGUES (Teal) ---
            ("Anglais Pro", "#14B8A6"),
            ("Leadership", "#0D9488"),
            ("Prise de parole", "#0F766E"),
            ("Organisation", "#CCFBF1"),
            ("Esprit critique", "#99F6E4"),
            ("Travail d'équipe", "#5EEAD4"),
            ("Mandarin", "#2DD4BF"),
            ("Rédaction", "#20B2AA"),
            ("Événementiel", "#115E59"),
            ("Pédagogie", "#134E4A"),
        ]

        self.stdout.write(self.style.WARNING(f"⏳ Analyse de {len(competences_data)} compétences..."))

        compteur_ajout = 0
        compteur_exist = 0

        for nom, couleur in competences_data:
            # get_or_create empêche les doublons si tu lances la commande 2 fois
            obj, created = Competence.objects.get_or_create(
                nom=nom,
                defaults={'couleur': couleur}
            )
            
            if created:
                compteur_ajout += 1
            else:
                compteur_exist += 1

        if compteur_ajout > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ Succès : {compteur_ajout} compétences ajoutées !"))
        
        if compteur_exist > 0:
            self.stdout.write(self.style.NOTICE(f"ℹ️ Info : {compteur_exist} compétences existaient déjà."))