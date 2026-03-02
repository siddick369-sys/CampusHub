from django.core.management.base import BaseCommand
from django.db import transaction

from orientation.models import (
    Track,
    Question,
    Choice,
    ChoiceTrackScore,
)


class Command(BaseCommand):
    help = "Remplit les tables du module Orientation avec des filières, questions, choix et scores."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- Debut du remplissage du module Orientation ---"))

        self.create_tracks()
        self.create_questions_choices()

        self.stdout.write(self.style.SUCCESS("OK: Donnees d'orientation creees / mises a jour avec succes."))

    # ----------------------------------------------------
    # 1) FILIÈRES (Track)
    # ----------------------------------------------------
    def create_tracks(self):
        tracks_data = [
            {
                "code": "INF-LIC",
                "name": "Informatique",
                "short_name": "Info",
                "domain": "stem",
                "difficulty": 3,
                "typical_duration_years": 3,
                "description": "Études en programmation, algorithmique, systèmes et réseaux.",
                "main_skills": "Programmation, Algorithmique, Bases de données, Réseaux",
                "soft_skills": "Logique, résolution de problèmes, travail en équipe",
                "recommended_profiles": "Élèves à l’aise avec les maths, la logique et les outils numériques.",
                "future_outlook": "rising",
            },
            {
                "code": "BUS-MGT",
                "name": "Gestion / Management",
                "short_name": "Management",
                "domain": "business",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Filière orientée vers la gestion d’entreprise, le management et le marketing.",
                "main_skills": "Gestion, Marketing, Comptabilité, Communication",
                "soft_skills": "Leadership, sens de l’organisation, communication",
                "recommended_profiles": "Élèves qui aiment organiser, communiquer, entreprendre.",
                "future_outlook": "rising",
            },
            {
                "code": "SANT-LIC",
                "name": "Sciences de la santé",
                "short_name": "Santé",
                "domain": "health",
                "difficulty": 4,
                "typical_duration_years": 6,
                "description": "Filière orientée médecine, soins infirmiers, pharmacie, etc.",
                "main_skills": "Biologie, Anatomie, Physiologie, Sciences médicales",
                "soft_skills": "Empathie, rigueur, gestion du stress",
                "recommended_profiles": "Élèves qui veulent aider les autres et sont prêts à fournir un gros effort.",
                "future_outlook": "rising",
            },
            {
                "code": "SOC-SCI",
                "name": "Sciences sociales",
                "short_name": "Socio",
                "domain": "social",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Études sur le fonctionnement des sociétés, psychologie, sociologie.",
                "main_skills": "Analyse, Rédaction, Esprit critique",
                "soft_skills": "Écoute, curiosité, ouverture d’esprit",
                "recommended_profiles": "Élèves intéressés par l’humain, la société et les comportements.",
                "future_outlook": "stable",
            },
            {
                "code": "ART-DES",
                "name": "Arts / Design",
                "short_name": "Arts",
                "domain": "arts",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Filière orientée vers la création graphique, design, audiovisuel.",
                "main_skills": "Dessin, Outils de design, Créativité",
                "soft_skills": "Sens esthétique, imagination, curiosité",
                "recommended_profiles": "Élèves créatifs, qui aiment créer, dessiner, concevoir.",
                "future_outlook": "rising",
            },
            {
                "code": "CIV-ENG",
                "name": "Génie Civil",
                "short_name": "Génie Civil",
                "domain": "stem",
                "difficulty": 4,
                "typical_duration_years": 5,
                "description": "Conception et construction de bâtiments, ponts et infrastructures.",
                "main_skills": "Physique, Mathématiques, RDM, CAO",
                "soft_skills": "Précision, sens des responsabilités, vision spatiale",
                "recommended_profiles": "Élèves passionnés par la construction et les sciences de l'ingénieur.",
                "future_outlook": "rising",
            },
            {
                "code": "LAW-LIC",
                "name": "Droit",
                "short_name": "Droit",
                "domain": "social",
                "difficulty": 4,
                "typical_duration_years": 3,
                "description": "Études des lois, de la justice et du cadre juridique de la société.",
                "main_skills": "Raisonnement juridique, Analyse de textes, Rédaction",
                "soft_skills": "Rigueur, éloquence, sens de la justice",
                "recommended_profiles": "Élèves aimant lire, analyser et argumenter.",
                "future_outlook": "stable",
            },
            {
                "code": "COM-JOU",
                "name": "Communication & Journalisme",
                "short_name": "Com",
                "domain": "social",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Journalisme, relations publiques, communication institutionnelle et digitale.",
                "main_skills": "Rédaction, Médias, Expression orale, Réseaux Sociaux",
                "soft_skills": "Curiosité, aisance relationnelle, réactivité",
                "recommended_profiles": "Élèves curieux du monde, qui aiment écrire et communiquer.",
                "future_outlook": "rising",
            },
            {
                "code": "AGR-SCI",
                "name": "Agronomie",
                "short_name": "Agro",
                "domain": "stem",
                "difficulty": 3,
                "typical_duration_years": 5,
                "description": "Sciences de l'agriculture, gestion des sols et production animale.",
                "main_skills": "Biologie végétale, Élevage, Gestion agricole",
                "soft_skills": "Patience, sens de l'observation, respect de la nature",
                "recommended_profiles": "Élèves aimant la nature et souhaitant relever les défis alimentaires.",
                "future_outlook": "rising",
            },
            {
                "code": "TRM-HOT",
                "name": "Tourisme & Hôtellerie",
                "short_name": "Tourisme",
                "domain": "business",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Gestion d'hôtels, restaurants et services liés au voyage.",
                "main_skills": "Langues, Gestion hôtelière, Marketing touristique",
                "soft_skills": "Hospitalité, polyvalence, sens du service",
                "recommended_profiles": "Élèves accueillants, aimant les langues et le voyage.",
                "future_outlook": "stable",
            },
            {
                "code": "ARC-DES",
                "name": "Architecture",
                "short_name": "Archi",
                "domain": "arts",
                "difficulty": 4,
                "typical_duration_years": 5,
                "description": "L'art de concevoir des espaces de vie et des bâtiments esthétiques.",
                "main_skills": "Conception spatiale, Histoire de l'art, CAO/DAO",
                "soft_skills": "Créativité, rigueur technique, sens esthétique",
                "recommended_profiles": "Élèves créatifs avec un bon esprit scientifique.",
                "future_outlook": "stable",
            },
            {
                "code": "PSY-SOC",
                "name": "Psychologie",
                "short_name": "Psycho",
                "domain": "social",
                "difficulty": 3,
                "typical_duration_years": 5,
                "description": "Étude des processus mentaux, des comportements et de la santé psychique.",
                "main_skills": "Psychopathologie, Analyse, Recherche scientifique",
                "soft_skills": "Écoute active, empathie, discrétion",
                "recommended_profiles": "Élèves intéressés par le fonctionnement de l'esprit humain.",
                "future_outlook": "rising",
            },
            {
                "code": "MKT-DIG",
                "name": "Marketing Digital",
                "short_name": "Mkt Dig",
                "domain": "business",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Stratégies de vente et communication sur Internet et les réseaux sociaux.",
                "main_skills": "SEO, E-commerce, Analytics, Copywriting",
                "soft_skills": "Créativité, adaptabilité, sens de l'analyse",
                "recommended_profiles": "Élèves connectés, créatifs et intéressés par les données.",
                "future_outlook": "rising",
            },
            {
                "code": "ENE-REN",
                "name": "Énergies Renouvelables",
                "short_name": "EnR",
                "domain": "stem",
                "difficulty": 4,
                "typical_duration_years": 5,
                "description": "Technologies des énergies propres (solaire, éolien, biomasse).",
                "main_skills": "Électrotechnique, Thermodynamique, Gestion de l'énergie",
                "soft_skills": "Conscience écologique, innovation, rigueur",
                "recommended_profiles": "Élèves souhaitant agir pour la transition énergétique.",
                "future_outlook": "rising",
            },
            {
                "code": "HUM-RES",
                "name": "Ressources Humaines",
                "short_name": "RH",
                "domain": "business",
                "difficulty": 2,
                "typical_duration_years": 3,
                "description": "Gestion du personnel, recrutement, paie et droit du travail.",
                "main_skills": "Recrutement, Droit social, Gestion de la paie",
                "soft_skills": "Médiation, sens humain, organisation",
                "recommended_profiles": "Élèves organisés, avec un bon relationnel et le sens de l'équité.",
                "future_outlook": "stable",
            },
        ]

        for data in tracks_data:
            track, created = Track.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "short_name": data["short_name"],
                    "domain": data["domain"],
                    "difficulty": data["difficulty"],
                    "typical_duration_years": data["typical_duration_years"],
                    "description": data["description"],
                    "main_skills": data["main_skills"],
                    "soft_skills": data["soft_skills"],
                    "recommended_profiles": data["recommended_profiles"],
                    "future_outlook": data["future_outlook"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + Filiere creee : {track.name}"))
            else:
                # On met à jour certains champs en cas de modification du script
                track.name = data["name"]
                track.short_name = data["short_name"]
                track.domain = data["domain"]
                track.difficulty = data["difficulty"]
                track.typical_duration_years = data["typical_duration_years"]
                track.description = data["description"]
                track.main_skills = data["main_skills"]
                track.soft_skills = data["soft_skills"]
                track.recommended_profiles = data["recommended_profiles"]
                track.future_outlook = data["future_outlook"]
                track.is_active = True
                track.save()
                self.stdout.write(self.style.WARNING(f"  * Filiere mise a jour : {track.name}"))

    # ----------------------------------------------------
    # 2) QUESTIONS + CHOIX + SCORES
    # ----------------------------------------------------
    def create_questions_choices(self):
        """
        Crée 20 questions d’orientation, les choix possibles,
        et relie chaque choix à une ou plusieurs filières avec un score.
        """
        tracks_by_code = {t.code: t for t in Track.objects.all()}

        questions_data = [
            {
                "text": "Qu’est-ce que tu aimes le plus faire dans ton temps libre ou à l’école ?",
                "category": "interest",
                "order": 1,
                "choices": [
                    {
                        "text": "Résoudre des problèmes sur ordinateur, programmer, bidouiller des logiciels.",
                        "track_scores": {"INF-LIC": 5},
                    },
                    {
                        "text": "Organiser des projets, gérer une petite équipe, vendre des choses.",
                        "track_scores": {"BUS-MGT": 5, "HUM-RES": 3},
                    },
                    {
                        "text": "Aider des personnes, écouter leurs problèmes, être utile à leur bien-être.",
                        "track_scores": {"SANT-LIC": 4, "SOC-SCI": 2, "PSY-SOC": 4},
                    },
                    {
                        "text": "Observer les comportements, débattre, analyser la société.",
                        "track_scores": {"SOC-SCI": 5, "LAW-LIC": 3},
                    },
                    {
                        "text": "Dessiner, créer des visuels, faire du montage vidéo ou photo.",
                        "track_scores": {"ART-DES": 5, "ARC-DES": 3, "MKT-DIG": 2},
                    },
                    {
                        "text": "Concevoir des bâtiments, des infrastructures ou travailler sur des chantiers techniques.",
                        "track_scores": {"CIV-ENG": 5, "ARC-DES": 4},
                    },
                    {
                        "text": "Travailler pour la protection de l'environnement, l'agriculture durable ou les énergies du futur.",
                        "track_scores": {"AGR-SCI": 5, "ENE-REN": 5},
                    },
                    {
                        "text": "Voyager, organiser des événements ou informer le public via les médias.",
                        "track_scores": {"TRM-HOT": 5, "COM-JOU": 5},
                    },
                ],
            },
            {
                "text": "Dans quelles matières te sens-tu le plus à l’aise ?",
                "category": "skill",
                "order": 2,
                "choices": [
                    {
                        "text": "Maths, physique, logique.",
                        "track_scores": {"INF-LIC": 4, "CIV-ENG": 4, "ENE-REN": 4},
                    },
                    {
                        "text": "Économie, gestion, marketing.",
                        "track_scores": {"BUS-MGT": 4, "MKT-DIG": 4, "HUM-RES": 3},
                    },
                    {
                        "text": "SVT, biologie, chimie.",
                        "track_scores": {"SANT-LIC": 4, "AGR-SCI": 4},
                    },
                    {
                        "text": "Histoire-géo, français, philosophie.",
                        "track_scores": {"SOC-SCI": 4, "LAW-LIC": 5, "COM-JOU": 4, "PSY-SOC": 3},
                    },
                    {
                        "text": "Arts plastiques, design, dessin.",
                        "track_scores": {"ART-DES": 4, "ARC-DES": 4},
                    },
                ],
            },
            {
                "text": "Quel type d’environnement de travail t’attire le plus ?",
                "category": "personality",
                "order": 3,
                "choices": [
                    {
                        "text": "Bureau avec ordinateur, projets techniques, ambiance startup ou tech.",
                        "track_scores": {"INF-LIC": 3, "BUS-MGT": 1},
                    },
                    {
                        "text": "Entreprise, open-space, réunions, contact avec des clients.",
                        "track_scores": {"BUS-MGT": 3},
                    },
                    {
                        "text": "Hôpital, clinique, cabinet de conseil ou de psychologie.",
                        "track_scores": {"SANT-LIC": 3, "PSY-SOC": 3},
                    },
                    {
                        "text": "Sur le terrain : chantiers, exploitations agricoles, sites industriels.",
                        "track_scores": {"CIV-ENG": 3, "AGR-SCI": 3, "ENE-REN": 3},
                    },
                    {
                        "text": "Tribunal, cabinet d'avocats, rédaction presse ou agence de com.",
                        "track_scores": {"LAW-LIC": 4, "COM-JOU": 4},
                    },
                    {
                        "text": "Hôtel, agence de voyage, environnement international.",
                        "track_scores": {"TRM-HOT": 4},
                    },
                    {
                        "text": "Studio de création, agence web, cabinet d'architecture.",
                        "track_scores": {"ART-DES": 3, "MKT-DIG": 2, "ARC-DES": 3},
                    },
                ],
            },
            {
                "text": "Comment préfères-tu travailler ?",
                "category": "personality",
                "order": 4,
                "choices": [
                    {
                        "text": "Seul(e) devant un ordinateur, concentré(e) sur des tâches techniques.",
                        "track_scores": {"INF-LIC": 4, "ART-DES": 2},
                    },
                    {
                        "text": "En équipe, à discuter, à organiser les tâches de chacun.",
                        "track_scores": {"BUS-MGT": 4, "SOC-SCI": 1},
                    },
                    {
                        "text": "Au contact direct des gens, en les aidant ou en les accompagnant.",
                        "track_scores": {"SANT-LIC": 3, "SOC-SCI": 3},
                    },
                    {
                        "text": "En créant des choses visuelles, en testant des idées créatives.",
                        "track_scores": {"ART-DES": 4},
                    },
                ],
            },
            {
                "text": "Quel type de problèmes aimes-tu le plus résoudre ?",
                "category": "interest",
                "order": 5,
                "choices": [
                    {
                        "text": "Des bugs, des problèmes techniques, des structures complexes.",
                        "track_scores": {"INF-LIC": 5, "CIV-ENG": 4, "ENE-REN": 4},
                    },
                    {
                        "text": "Des problèmes de conflits humains, de droit ou de psychologie.",
                        "track_scores": {"LAW-LIC": 5, "PSY-SOC": 5, "HUM-RES": 4},
                    },
                    {
                        "text": "Comment mieux produire de la nourriture ou gérer l'énergie.",
                        "track_scores": {"AGR-SCI": 5, "ENE-REN": 5},
                    },
                    {
                        "text": "Des questions de communication, d'image de marque ou d'information.",
                        "track_scores": {"COM-JOU": 5, "MKT-DIG": 5},
                    },
                    {
                        "text": "Comment rendre un bâtiment ou un espace harmonieux et fonctionnel.",
                        "track_scores": {"ARC-DES": 5, "ART-DES": 2},
                    },
                ],
            },
            {
                "text": "Si tu devais choisir un projet de fin d’année, tu préférerais :",
                "category": "interest",
                "order": 6,
                "choices": [
                    {
                        "text": "Créer un site web ou une application mobile.",
                        "track_scores": {"INF-LIC": 5, "ART-DES": 1},
                    },
                    {
                        "text": "Monter un mini-business, une campagne marketing ou un projet entrepreneurial.",
                        "track_scores": {"BUS-MGT": 5},
                    },
                    {
                        "text": "Faire un projet sur une maladie, la nutrition ou la santé.",
                        "track_scores": {"SANT-LIC": 5},
                    },
                    {
                        "text": "Préparer une enquête ou un documentaire sur un sujet de société.",
                        "track_scores": {"SOC-SCI": 5},
                    },
                    {
                        "text": "Créer une BD, un court métrage, un logo ou une identité visuelle.",
                        "track_scores": {"ART-DES": 5},
                    },
                ],
            },
            {
                "text": "Comment te sens-tu par rapport aux longues études ?",
                "category": "value",
                "order": 7,
                "choices": [
                    {
                        "text": "Je suis prêt(e) à faire des études longues et difficiles si le métier me passionne.",
                        "track_scores": {"SANT-LIC": 4, "INF-LIC": 2},
                    },
                    {
                        "text": "Je préfère des études raisonnables (3 à 4 ans) puis entrer vite dans la vie active.",
                        "track_scores": {"BUS-MGT": 3, "ART-DES": 2, "SOC-SCI": 2},
                    },
                    {
                        "text": "Je voudrais plutôt un parcours court, concret, avec un métier rapidement.",
                        "track_scores": {"BUS-MGT": 2, "ART-DES": 3},
                    },
                ],
            },
            {
                "text": "Qu’est-ce qui est le plus important pour toi dans ton futur métier ?",
                "category": "value",
                "order": 8,
                "choices": [
                    {
                        "text": "La sécurité de l’emploi et un bon salaire.",
                        "track_scores": {"INF-LIC": 3, "SANT-LIC": 3, "BUS-MGT": 2},
                    },
                    {
                        "text": "Faire quelque chose qui a du sens pour les autres.",
                        "track_scores": {"SANT-LIC": 4, "SOC-SCI": 3},
                    },
                    {
                        "text": "Être libre, créatif(ve), et pouvoir exprimer mes idées.",
                        "track_scores": {"ART-DES": 4, "INF-LIC": 1},
                    },
                    {
                        "text": "Avoir des responsabilités, gérer des projets, diriger des équipes.",
                        "track_scores": {"BUS-MGT": 4},
                    },
                ],
            },
            {
                "text": "Comment réagis-tu face au stress et à la pression ?",
                "category": "personality",
                "order": 9,
                "choices": [
                    {
                        "text": "Je gère plutôt bien, surtout si je suis sérieux(se) et bien préparé(e).",
                        "track_scores": {"SANT-LIC": 3, "INF-LIC": 2, "BUS-MGT": 2},
                    },
                    {
                        "text": "Je préfère les environnements où la pression reste raisonnable.",
                        "track_scores": {"SOC-SCI": 3, "ART-DES": 2},
                    },
                    {
                        "text": "Je n’aime pas du tout la pression, je préfère un rythme calme.",
                        "track_scores": {"ART-DES": 3, "SOC-SCI": 2},
                    },
                ],
            },
            {
                "text": "Dans un projet de groupe, quel rôle prends-tu le plus souvent ?",
                "category": "personality",
                "order": 10,
                "choices": [
                    {
                        "text": "La personne qui fait toute la partie technique (ex: code, montage…).",
                        "track_scores": {"INF-LIC": 4, "ART-DES": 2},
                    },
                    {
                        "text": "La personne qui organise, répartit les tâches, motive l’équipe.",
                        "track_scores": {"BUS-MGT": 4},
                    },
                    {
                        "text": "La personne qui analyse, rédige, fait les recherches.",
                        "track_scores": {"SOC-SCI": 4},
                    },
                    {
                        "text": "La personne qui pense au visuel, au rendu final, à la présentation.",
                        "track_scores": {"ART-DES": 4},
                    },
                ],
            },
            {
                "text": "Que penses-tu des outils numériques (ordinateur, applis, réseaux sociaux) ?",
                "category": "interest",
                "order": 11,
                "choices": [
                    {
                        "text": "Je les adore, j’aime comprendre comment ça marche et les utiliser à fond.",
                        "track_scores": {"INF-LIC": 5},
                    },
                    {
                        "text": "Je les utilise surtout pour communiquer et organiser des projets.",
                        "track_scores": {"BUS-MGT": 3, "SOC-SCI": 1},
                    },
                    {
                        "text": "Je les utilise, mais ce n’est pas ce qui m’intéresse le plus.",
                        "track_scores": {"SANT-LIC": 2, "SOC-SCI": 2},
                    },
                    {
                        "text": "Je m’en sers pour créer (montage, graphisme, musique…).",
                        "track_scores": {"ART-DES": 4},
                    },
                ],
            },
            {
                "text": "Te verrais-tu un jour créer ta propre activité (entreprise, studio, cabinet) ?",
                "category": "value",
                "order": 12,
                "choices": [
                    {
                        "text": "Oui, j’aimerais beaucoup entreprendre et créer mon propre projet.",
                        "track_scores": {"BUS-MGT": 5, "ART-DES": 2, "INF-LIC": 2},
                    },
                    {
                        "text": "Pourquoi pas, mais ce n’est pas ma priorité.",
                        "track_scores": {"INF-LIC": 2, "SOC-SCI": 1},
                    },
                    {
                        "text": "Non, je préfère être salarié(e) dans une structure existante.",
                        "track_scores": {"SANT-LIC": 3, "SOC-SCI": 2},
                    },
                ],
            },
            {
                "text": "La biologie, le corps humain, la santé, ça t’intéresse…",
                "category": "interest",
                "order": 13,
                "choices": [
                    {
                        "text": "Beaucoup, je pourrais en parler pendant longtemps.",
                        "track_scores": {"SANT-LIC": 5},
                    },
                    {
                        "text": "Un peu, mais ce n’est pas ce que je préfère.",
                        "track_scores": {"SOC-SCI": 1},},
                    {
                        "text": "Pas vraiment, je suis plus attiré(e) par d’autres domaines.",
                        "track_scores": {"INF-LIC": 2, "ART-DES": 1, "BUS-MGT": 1},
                    },
                ],
            },
            {
                "text": "Comment te sens-tu à l’idée de travailler régulièrement avec des personnes malades ou en difficulté ?",
                "category": "personality",
                "order": 14,
                "choices": [
                    {
                        "text": "Je me sentirais utile et prêt(e) à m’impliquer pour eux.",
                        "track_scores": {"SANT-LIC": 4, "SOC-SCI": 3},
                    },
                    {
                        "text": "Je préfère aider les gens autrement, sans être au contact de la maladie.",
                        "track_scores": {"SOC-SCI": 2, "BUS-MGT": 1},
                    },
                    {
                        "text": "Je ne me vois pas du tout dans ce type d’environnement.",
                        "track_scores": {"INF-LIC": 2, "ART-DES": 2},
                    },
                ],
            },
            {
                "text": "Te sens-tu à l’aise avec l’idée de parler en public ou de présenter un projet ?",
                "category": "skill",
                "order": 15,
                "choices": [
                    {
                        "text": "Oui, j’aime prendre la parole devant les autres.",
                        "track_scores": {"BUS-MGT": 4, "SOC-SCI": 2},
                    },
                    {
                        "text": "Je peux le faire si nécessaire, même si je stresse un peu.",
                        "track_scores": {"SANT-LIC": 2, "INF-LIC": 1},
                    },
                    {
                        "text": "Je n’aime pas du tout parler en public, je préfère rester en coulisses.",
                        "track_scores": {"INF-LIC": 3, "ART-DES": 2},
                    },
                ],
            },
            {
                "text": "Quand tu réfléchis à ton futur métier, tu te vois plutôt…",
                "category": "value",
                "order": 16,
                "choices": [
                    {
                        "text": "Derrière un ordinateur, à gérer des projets techniques ou créatifs.",
                        "track_scores": {"INF-LIC": 4, "ART-DES": 3},
                    },
                    {
                        "text": "En interaction directe avec des clients, une équipe, des partenaires.",
                        "track_scores": {"BUS-MGT": 4, "SOC-SCI": 2},
                    },
                    {
                        "text": "Au contact des patients ou de personnes en difficulté.",
                        "track_scores": {"SANT-LIC": 4, "SOC-SCI": 2},
                    },
                ],
            },
            {
                "text": "Que penses-tu des chiffres, des tableaux, des statistiques ?",
                "category": "skill",
                "order": 17,
                "choices": [
                    {
                        "text": "J’aime bien, je trouve ça logique et intéressant.",
                        "track_scores": {"INF-LIC": 3, "BUS-MGT": 3},
                    },
                    {
                        "text": "Je m’en sors, mais ce n’est pas ce que je préfère.",
                        "track_scores": {"SOC-SCI": 2, "SANT-LIC": 1},
                    },
                    {
                        "text": "Je n’aime pas du tout les chiffres.",
                        "track_scores": {"ART-DES": 3, "SOC-SCI": 2},
                    },
                ],
            },
            {
                "text": "Te verrais-tu travailler dans un contexte international (langues étrangères, collaborations à distance) ?",
                "category": "value",
                "order": 18,
                "choices": [
                    {
                        "text": "Oui, ça me motive beaucoup.",
                        "track_scores": {"INF-LIC": 3, "BUS-MGT": 3, "ART-DES": 2},
                    },
                    {
                        "text": "Pourquoi pas, si c’est utile pour le métier.",
                        "track_scores": {"SANT-LIC": 2, "SOC-SCI": 2},
                    },
                    {
                        "text": "Je préfère rester dans un environnement local.",
                        "track_scores": {"SOC-SCI": 2, "ART-DES": 1},
                    },
                ],
            },
            {
                "text": "Quand tu travailles sur un projet, tu accordes le plus d’importance à :",
                "category": "personality",
                "order": 19,
                "choices": [
                    {
                        "text": "La qualité technique : que ce soit bien codé, bien structuré, efficace.",
                        "track_scores": {"INF-LIC": 4},
                    },
                    {
                        "text": "Le résultat concret pour le client ou l’organisation.",
                        "track_scores": {"BUS-MGT": 4},
                    },
                    {
                        "text": "L’impact humain ou social du projet.",
                        "track_scores": {"SOC-SCI": 4, "SANT-LIC": 2},
                    },
                    {
                        "text": "Le rendu visuel, la beauté, le style.",
                        "track_scores": {"ART-DES": 4},
                    },
                ],
            },
            {
                "text": "Si tu devais choisir un atelier thématique pour une semaine, tu prendrais :",
                "category": "interest",
                "order": 20,
                "choices": [
                    {
                        "text": "Initiation au développement web / mobile.",
                        "track_scores": {"INF-LIC": 5},
                    },
                    {
                        "text": "Création d’un business plan et d’un projet entrepreneurial.",
                        "track_scores": {"BUS-MGT": 5},
                    },
                    {
                        "text": "Découverte du milieu hospitalier et des métiers de la santé.",
                        "track_scores": {"SANT-LIC": 5},
                    },
                    {
                        "text": "Atelier sur les questions de société (égalité, environnement, justice…).",
                        "track_scores": {"SOC-SCI": 5},
                    },
                    {
                        "text": "Atelier de design graphique, vidéo, photo ou animation.",
                        "track_scores": {"ART-DES": 5},
                    },
                ],
            },
        ]

        for q_data in questions_data:
            question, q_created = Question.objects.get_or_create(
                text=q_data["text"],
                defaults={
                    "category": q_data["category"],
                    "order": q_data["order"],
                    "is_active": True,
                },
            )

            if q_created:
                self.stdout.write(self.style.SUCCESS(f"  + Question creee : {question.text[:60]}"))
            else:
                question.category = q_data["category"]
                question.order = q_data["order"]
                question.is_active = True
                question.save()
                self.stdout.write(self.style.WARNING(f"  * Question mise a jour : {question.text[:60]}"))

            for choice_data in q_data["choices"]:
                choice, c_created = Choice.objects.get_or_create(
                    question=question,
                    text=choice_data["text"],
                )

                if c_created:
                    self.stdout.write(self.style.SUCCESS(f"    + Choix cree : {choice.text[:60]}"))
                else:
                    self.stdout.write(self.style.WARNING(f"    - Choix deja existant : {choice.text[:60]}"))

                for track_code, score in choice_data["track_scores"].items():
                    track = tracks_by_code.get(track_code)
                    if not track:
                        self.stdout.write(self.style.ERROR(f"      [!] Track introuvable pour code {track_code}"))
                        continue

                    cts, s_created = ChoiceTrackScore.objects.get_or_create(
                        choice=choice,
                        track=track,
                        defaults={"score": score},
                    )
                    if not s_created:
                        cts.score = score
                        cts.save()
                        self.stdout.write(
                            self.style.WARNING(
                                f"      * Score mis a jour : {choice.text[:30]} -> {track.name} = {score}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"      + Score cree : {choice.text[:30]} -> {track.name} = {score}"
                            )
                        )
