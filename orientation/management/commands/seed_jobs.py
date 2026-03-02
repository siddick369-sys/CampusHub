from django.core.management.base import BaseCommand
from django.db import transaction
from orientation.models import Track, Job, JobTrackRelevance

class Command(BaseCommand):
    help = "Remplit la table des métiers avec 90 profils populaires et crée les liaisons."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🚀 Lancement de la base de données massive (90 métiers)…"))

        # Dictionnaire des métiers classés par code de filière (18 métiers par track)
        jobs_by_track = {
            "INF-LIC": [
                {"title": "Développeur Fullstack Django", "sector": "IT", "min": 350000, "max": 900000, "demand": "high", "remote": True},
                {"title": "Analyste Cybersécurité", "sector": "IT", "min": 450000, "max": 1200000, "demand": "high", "remote": False},
                {"title": "Ingénieur Cloud & DevOps", "sector": "IT", "min": 500000, "max": 1500000, "demand": "high", "remote": True},
                {"title": "Data Scientist", "sector": "Data", "min": 600000, "max": 1800000, "demand": "high", "remote": True},
                {"title": "Administrateur Réseaux", "sector": "Télécoms", "min": 300000, "max": 800000, "demand": "medium", "remote": False},
                {"title": "Développeur Mobile Flutter", "sector": "IT", "min": 300000, "max": 750000, "demand": "high", "remote": True},
                {"title": "Consultant ERP SAP", "sector": "IT", "min": 400000, "max": 1100000, "demand": "medium", "remote": False},
                {"title": "Chef de Projet IT", "sector": "IT", "min": 500000, "max": 1300000, "demand": "medium", "remote": False},
                {"title": "Ingénieur IA / ML", "sector": "Data", "min": 700000, "max": 2000000, "demand": "high", "remote": True},
                {"title": "Administrateur de Bases de Données", "sector": "IT", "min": 350000, "max": 850000, "demand": "medium", "remote": False},
                {"title": "Ingénieur Systèmes Embarqués", "sector": "STEM", "min": 400000, "max": 950000, "demand": "medium", "remote": False},
                {"title": "Technicien Support Informatique", "sector": "IT", "min": 150000, "max": 350000, "demand": "high", "remote": False},
                {"title": "Architecte Logiciel", "sector": "IT", "min": 700000, "max": 1800000, "demand": "high", "remote": True},
                {"title": "Développeur Blockchain", "sector": "IT", "min": 600000, "max": 1600000, "demand": "medium", "remote": True},
                {"title": "Analyste Business Intelligence", "sector": "Data", "min": 400000, "max": 950000, "demand": "high", "remote": True},
                {"title": "Expert en Domotique", "sector": "STEM", "min": 250000, "max": 600000, "demand": "medium", "remote": False},
                {"title": "Ingénieur Hardware", "sector": "STEM", "min": 350000, "max": 850000, "demand": "low", "remote": False},
                {"title": "Testeur QA Automatisé", "sector": "IT", "min": 250000, "max": 650000, "demand": "high", "remote": True},
            ],
            "BUS-MGT": [
                {"title": "Expert-Comptable", "sector": "Finance", "min": 400000, "max": 1500000, "demand": "high", "remote": False},
                {"title": "Marketing Manager", "sector": "Commerce", "min": 250000, "max": 750000, "demand": "high", "remote": True},
                {"title": "Analyste Financier", "sector": "Banque", "min": 350000, "max": 1100000, "demand": "medium", "remote": False},
                {"title": "Directeur Commercial", "sector": "Ventes", "min": 500000, "max": 2500000, "demand": "high", "remote": False},
                {"title": "Responsable Logistique", "sector": "Supply Chain", "min": 250000, "max": 650000, "demand": "high", "remote": False},
                {"title": "Auditeur Interne", "sector": "Finance", "min": 350000, "max": 950000, "demand": "medium", "remote": False},
                {"title": "Chef de Produit", "sector": "Marketing", "min": 300000, "max": 800000, "demand": "medium", "remote": True},
                {"title": "Gestionnaire de Patrimoine", "sector": "Banque", "min": 400000, "max": 1200000, "demand": "medium", "remote": False},
                {"title": "Responsable RH", "sector": "Management", "min": 350000, "max": 1100000, "demand": "medium", "remote": False},
                {"title": "Contrôleur de Gestion", "sector": "Finance", "min": 300000, "max": 850000, "demand": "high", "remote": False},
                {"title": "Business Developer", "sector": "Commerce", "min": 250000, "max": 900000, "demand": "high", "remote": True},
                {"title": "Manager de Projet", "sector": "Management", "min": 400000, "max": 1200000, "demand": "medium", "remote": False},
                {"title": "Courtier en Assurance", "sector": "Assurance", "min": 200000, "max": 700000, "demand": "medium", "remote": False},
                {"title": "Responsable Achats", "sector": "Supply Chain", "min": 300000, "max": 800000, "demand": "medium", "remote": False},
                {"title": "Consultant en Stratégie", "sector": "Conseil", "min": 500000, "max": 2000000, "demand": "high", "remote": True},
                {"title": "Trader", "sector": "Finance", "min": 600000, "max": 3000000, "demand": "low", "remote": True},
                {"title": "Entrepreneur / Startupper", "sector": "Business", "min": 0, "max": 5000000, "demand": "high", "remote": True},
                {"title": "Directeur d'Agence Bancaire", "sector": "Banque", "min": 500000, "max": 1500000, "demand": "medium", "remote": False},
            ],
            "SANT-LIC": [
                {"title": "Infirmier Major", "sector": "Santé", "min": 200000, "max": 450000, "demand": "high", "remote": False},
                {"title": "Docteur Généraliste", "sector": "Médecine", "min": 450000, "max": 1500000, "demand": "high", "remote": False},
                {"title": "Pharmacien Industriel", "sector": "Pharmacie", "min": 350000, "max": 1000000, "demand": "medium", "remote": False},
                {"title": "Technicien de Labo", "sector": "Santé", "min": 180000, "max": 400000, "demand": "medium", "remote": False},
                {"title": "Chirurgien Dentiste", "sector": "Santé", "min": 500000, "max": 2000000, "demand": "high", "remote": False},
                {"title": "Kinésithérapeute", "sector": "Rééducation", "min": 200000, "max": 600000, "demand": "medium", "remote": False},
                {"title": "Sage-Femme / Maïeuticien", "sector": "Santé", "min": 180000, "max": 400000, "demand": "high", "remote": False},
                {"title": "Opticien", "sector": "Santé", "min": 200000, "max": 550000, "demand": "medium", "remote": False},
                {"title": "Délégué Médical", "sector": "Commerce", "min": 250000, "max": 750000, "demand": "high", "remote": False},
                {"title": "Nutritionniste", "sector": "Santé", "min": 150000, "max": 500000, "demand": "medium", "remote": True},
                {"title": "Anesthésiste Réanimateur", "sector": "Médecine", "min": 600000, "max": 2500000, "demand": "high", "remote": False},
                {"title": "Radiologue", "sector": "Santé", "min": 500000, "max": 2200000, "demand": "high", "remote": False},
                {"title": "Psychologue Clinicien", "sector": "Santé", "min": 200000, "max": 700000, "demand": "medium", "remote": True},
                {"title": "Gestionnaire d'Hôpital", "sector": "Management Santé", "min": 400000, "max": 1200000, "demand": "medium", "remote": False},
                {"title": "Biologiste Médical", "sector": "Recherche", "min": 350000, "max": 900000, "demand": "medium", "remote": False},
                {"title": "Ergothérapeute", "sector": "Santé", "min": 200000, "max": 550000, "demand": "low", "remote": False},
                {"title": "Ingénieur Biomédical", "sector": "STEM", "min": 350000, "max": 950000, "demand": "medium", "remote": False},
                {"title": "Responsable QHSE Santé", "sector": "Qualité", "min": 300000, "max": 800000, "demand": "high", "remote": False},
            ],
            "SOC-SCI": [
                {"title": "Juriste d'Affaires", "sector": "Droit", "min": 350000, "max": 1200000, "demand": "high", "remote": False},
                {"title": "Sociologue d'Étude", "sector": "Social", "min": 200000, "max": 550000, "demand": "low", "remote": False},
                {"title": "Journaliste", "sector": "Média", "min": 150000, "max": 600000, "demand": "medium", "remote": True},
                {"title": "Diplomate / Ambassadeur", "sector": "Relations Int.", "min": 800000, "max": 3500000, "demand": "low", "remote": False},
                {"title": "Assistant Social", "sector": "Social", "min": 150000, "max": 350000, "demand": "high", "remote": False},
                {"title": "Chargé de Com Interne", "sector": "Com", "min": 200000, "max": 550000, "demand": "medium", "remote": True},
                {"title": "Conseiller d'Orientation", "sector": "Éducation", "min": 180000, "max": 450000, "demand": "medium", "remote": False},
                {"title": "Anthropologue", "sector": "Recherche", "min": 250000, "max": 650000, "demand": "low", "remote": False},
                {"title": "Consultant RH Senior", "sector": "Management", "min": 450000, "max": 1300000, "demand": "high", "remote": True},
                {"title": "Généalogiste", "sector": "Social", "min": 150000, "max": 400000, "demand": "low", "remote": True},
                {"title": "Expert en Politiques Publiques", "sector": "Gouvernance", "min": 500000, "max": 1800000, "demand": "medium", "remote": False},
                {"title": "Archiviste Digital", "sector": "Culture", "min": 180000, "max": 450000, "demand": "medium", "remote": False},
                {"title": "Urbaniste", "sector": "STEM/Social", "min": 300000, "max": 900000, "demand": "medium", "remote": False},
                {"title": "Médiateur Familial", "sector": "Social", "min": 150000, "max": 400000, "demand": "medium", "remote": False},
                {"title": "Attaché de Presse", "sector": "Com", "min": 250000, "max": 650000, "demand": "medium", "remote": True},
                {"title": "Documentaliste", "sector": "Éducation", "min": 150000, "max": 350000, "demand": "low", "remote": False},
                {"title": "Interprète de Conférence", "sector": "Langues", "min": 300000, "max": 1000000, "demand": "high", "remote": True},
                {"title": "Politologue", "sector": "Recherche", "min": 250000, "max": 750000, "demand": "low", "remote": False},
            ],
            "ART-DES": [
                {"title": "UI/UX Designer", "sector": "Design Digital", "min": 350000, "max": 950000, "demand": "high", "remote": True},
                {"title": "Architecte d'Intérieur", "sector": "Architecture", "min": 350000, "max": 1200000, "demand": "medium", "remote": False},
                {"title": "Motion Designer", "sector": "Audiovisuel", "min": 300000, "max": 800000, "demand": "high", "remote": True},
                {"title": "Directeur Artistique", "sector": "Publicité", "min": 500000, "max": 1500000, "demand": "high", "remote": False},
                {"title": "Illustrateur Freelance", "sector": "Arts", "min": 150000, "max": 600000, "demand": "medium", "remote": True},
                {"title": "Photographe Mode", "sector": "Arts", "min": 200000, "max": 800000, "demand": "medium", "remote": False},
                {"title": "Styliste / Modéliste", "sector": "Mode", "min": 200000, "max": 700000, "demand": "medium", "remote": False},
                {"title": "Concept Artist Jeu Vidéo", "sector": "Gaming", "min": 400000, "max": 1100000, "demand": "medium", "remote": True},
                {"title": "Monteur Vidéo Pro", "sector": "Audiovisuel", "min": 250000, "max": 650000, "demand": "high", "remote": True},
                {"title": "Web Designer", "sector": "Design Digital", "min": 250000, "max": 600000, "demand": "high", "remote": True},
                {"title": "Scénographe", "sector": "Spectacle", "min": 300000, "max": 850000, "demand": "low", "remote": False},
                {"title": "Dessinateur BD", "sector": "Arts", "min": 100000, "max": 500000, "demand": "low", "remote": True},
                {"title": "Graphic Designer 2D/3D", "sector": "Publicité", "min": 200000, "max": 550000, "demand": "high", "remote": True},
                {"title": "Maquilleur Pro", "sector": "Cinéma/Mode", "min": 150000, "max": 450000, "demand": "medium", "remote": False},
                {"title": "Décorateur de Plateau", "sector": "Audiovisuel", "min": 250000, "max": 600000, "demand": "low", "remote": False},
                {"title": "Product Designer", "sector": "Industrie", "min": 400000, "max": 1000000, "demand": "medium", "remote": False},
                {"title": "Expert UX Research", "sector": "Digital", "min": 400000, "max": 1100000, "demand": "medium", "remote": True},
                {"title": "Calligraphe / Typographe", "sector": "Arts", "min": 150000, "max": 400000, "demand": "low", "remote": True},
            ]
        }

        count = 0
        for track_code, job_list in jobs_by_track.items():
            try:
                track = Track.objects.get(code=track_code)
                for item in job_list:
                    job, created = Job.objects.update_or_create(
                        title=item["title"],
                        defaults={
                            "sector": item["sector"],
                            "typical_salary_min": item["min"],
                            "typical_salary_max": item["max"],
                            "salary_currency": "FCFA",
                            "demand_level": item["demand"],
                            "remote_friendly": item["remote"],
                            "description": f"Découvrez les opportunités pour le métier de {item['title']} dans le secteur {item['sector']}.",
                            "main_tasks": "1. Missions quotidiennes\n2. Gestion de projets\n3. Collaboration inter-services.",
                            "required_hard_skills": "Compétences techniques spécifiques au rôle.",
                            "required_soft_skills": "Communication, adaptabilité et esprit critique.",
                        }
                    )
                    JobTrackRelevance.objects.get_or_create(job=job, track=track, defaults={"relevance_score": 5})
                    if created: count += 1
            except Track.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Track {track_code} introuvable !"))

        self.stdout.write(self.style.SUCCESS(f"✅ Remplissage terminé : {count} nouveaux métiers ajoutés !"))