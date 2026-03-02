import random
from django.core.management.base import BaseCommand
from faker import Faker
# REMPLACE 'incubation' PAR LE NOM DE TON APP SI DIFFÉRENT
from incubation.models import EtudiantTalent, Competence 

class Command(BaseCommand):
    help = 'Remplit la base de données avec des étudiants talentueux fictifs'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, help='Nombre de talents à créer')

    def handle(self, *args, **kwargs):
        total = kwargs['total']
        fake = Faker('fr_FR')  # Générateur de données en français

        self.stdout.write(self.style.WARNING(f'Création de {total} talents en cours...'))

        # 1. Création des Compétences (Tags)
        skills_list = [
            'Python', 'Django', 'ReactJS', 'Flutter', 'UI/UX Design', 
            'Marketing Digital', 'Data Science', 'Sécurité Réseau', 
            'Gestion de Projet', 'Comptabilité', 'Montage Vidéo', 'Anglais C1'
        ]
        
        db_skills = []
        for skill in skills_list:
            # get_or_create évite les doublons
            obj, created = Competence.objects.get_or_create(nom=skill)
            db_skills.append(obj)
            if created:
                self.stdout.write(f'- Compétence créée : {skill}')

        # 2. Liste des Filières IUT (Exemple)
        filieres = [
            'Génie Informatique', 'Génie Réseaux & Télécoms', 
            'Génie Biologique', 'Génie Mécanique', 
            'Gestion des Entreprises', 'Carrières Juridiques',
            'Génie Civil', 'Génie Industriel et Maintenance'
        ]

        # 3. Création des Étudiants
        for i in range(total):
            # Génération d'un numéro camerounais réaliste
            phone = f"+237 6{random.randint(50, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
            
            # Génération d'une moyenne réaliste pour un "Talent" (entre 12 et 19.5)
            moyenne = round(random.uniform(12.0, 19.5), 2)

            prenom = fake.first_name()
            nom = fake.last_name()
            nom_complet = f"{prenom} {nom}"
            
            # Création de l'objet
            etudiant = EtudiantTalent.objects.create(
                noms_prenoms=nom_complet,
                telephone=phone,
                adresse_email=f"{prenom.lower()}.{nom.lower()}@univ-ndere.cm",
                filiere=random.choice(filieres),
                moyenne_generale=moyenne,
                # photo=None (On laisse vide pour utiliser le placeholder du template)
            )

            # Ajout de 2 à 4 compétences aléatoires
            random_skills = random.sample(db_skills, k=random.randint(2, 4))
            etudiant.competences.set(random_skills)
            etudiant.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Succès ! {total} étudiants talents ont été ajoutés.'))