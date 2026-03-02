from django.core.management.base import BaseCommand
from django.db import transaction

from stages.models import QuickReply


class Command(BaseCommand):
    help = "Crée des modèles de réponses rapides par défaut pour les entreprises."

    DEFAULT_QUICK_REPLIES = [
        # --- 1. Accusés de réception / remerciements ---
        {
            "label": "Merci candidature",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre candidature et l'intérêt que vous portez à notre entreprise.\n"
                "Nous allons étudier votre profil et nous reviendrons vers vous dans les meilleurs délais.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Merci candidature (générique)",
            "text": (
                "Bonjour,\n\n"
                "Nous accusons réception de votre candidature.\n"
                "Notre équipe va analyser votre dossier et vous serez recontacté(e) si votre profil correspond à nos besoins.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 2. Demande de documents / infos complémentaires ---
        {
            "label": "Demande portfolio",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre candidature.\n"
                "Pour aller plus loin, pourriez-vous nous envoyer votre portfolio ou quelques projets "
                "représentatifs de vos compétences ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Demande CV à jour",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre intérêt.\n"
                "Pour compléter votre dossier, pourriez-vous nous transmettre un CV à jour au format PDF ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Demande informations complémentaires",
            "text": (
                "Bonjour,\n\n"
                "Merci pour l'intérêt que vous portez à notre offre.\n"
                "Afin de compléter votre dossier, pourriez-vous nous transmettre quelques informations "
                "supplémentaires (par exemple : disponibilité, localisation, expériences pertinentes, attentes de rémunération) ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 3. Entretien / test technique ---
        {
            "label": "Proposition entretien",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre candidature.\n"
                "Nous aimerions organiser un entretien avec vous pour échanger davantage sur votre profil.\n"
                "Pouvez-vous nous indiquer vos disponibilités sur les prochains jours ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Confirmation entretien (date/heure)",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre retour.\n"
                "Nous confirmons votre entretien le [DATE] à [HEURE], qui se déroulera [en présentiel / en visioconférence].\n"
                "Vous recevrez les détails pratiques prochainement.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Proposition test technique",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre candidature.\n"
                "Dans le cadre de notre processus de recrutement, nous aimerions vous proposer un test technique.\n"
                "Si vous êtes d'accord, nous vous enverrons les consignes et le délai de réalisation.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Relance test technique",
            "text": (
                "Bonjour,\n\n"
                "Nous revenons vers vous concernant le test technique qui vous a été proposé.\n"
                "L'avez-vous bien reçu, et pensez-vous pouvoir le réaliser dans les délais indiqués ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 4. Candidature positive / suite du process ---
        {
            "label": "Candidature retenue (suite process)",
            "text": (
                "Bonjour,\n\n"
                "Nous avons le plaisir de vous informer que votre candidature a été retenue pour la suite du processus.\n"
                "Nous reviendrons vers vous prochainement avec les prochaines étapes.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Proposition stage / poste",
            "text": (
                "Bonjour,\n\n"
                "Suite à nos échanges, nous serions intéressés par votre profil pour un stage / poste au sein de notre équipe.\n"
                "Nous vous proposerons prochainement une offre détaillant les conditions (durée, missions, rémunération, etc.).\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 5. Refus / clôture respectueuse ---
        {
            "label": "Candidature refusée",
            "text": (
                "Bonjour,\n\n"
                "Merci d'avoir candidaté et pour l'intérêt que vous portez à notre entreprise.\n"
                "Après étude attentive de votre profil, nous ne pouvons malheureusement pas donner une suite favorable "
                "à votre candidature.\n"
                "Nous vous souhaitons néanmoins une bonne continuation dans vos projets.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Refus avec encouragement",
            "text": (
                "Bonjour,\n\n"
                "Merci pour votre candidature et le temps consacré à notre processus.\n"
                "Après analyse, nous avons décidé de ne pas poursuivre avec votre profil pour ce poste.\n"
                "Cependant, votre parcours reste intéressant et nous vous encourageons à postuler à nouveau si une nouvelle "
                "opportunité correspond à vos compétences.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 6. Relances / suivi ---
        {
            "label": "Relance candidature",
            "text": (
                "Bonjour,\n\n"
                "Nous revenons vers vous concernant votre candidature.\n"
                "Êtes-vous toujours intéressé(e) par le poste ?\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Relance après entretien",
            "text": (
                "Bonjour,\n\n"
                "Suite à notre entretien, nous souhaitions savoir si vous êtes toujours intéressé(e) par l'opportunité "
                "au sein de notre entreprise.\n"
                "N'hésitez pas à nous faire part de vos questions éventuelles.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 7. Informations pratiques / organisation ---
        {
            "label": "Infos lieu entretien",
            "text": (
                "Bonjour,\n\n"
                "L'entretien aura lieu à l'adresse suivante :\n"
                "[Adresse complète]\n\n"
                "Merci de vous présenter [X] minutes en avance et de vous munir d'une pièce d'identité.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },
        {
            "label": "Infos entretien visio",
            "text": (
                "Bonjour,\n\n"
                "L'entretien se déroulera en visioconférence.\n"
                "Nous vous enverrons un lien de connexion (Zoom / Google Meet / autre) avant l'heure prévue.\n"
                "Merci de vérifier votre connexion internet et votre micro/caméra en amont.\n\n"
                "Cordialement,\n"
                "L'équipe recrutement."
            ),
        },

        # --- 8. Fin de stage / retour d'expérience ---
        {
            "label": "Fin de stage – remerciement",
            "text": (
                "Bonjour,\n\n"
                "Votre période de stage au sein de notre entreprise arrive à son terme.\n"
                "Nous tenions à vous remercier pour votre implication et votre travail.\n"
                "Nous vous souhaitons une bonne continuation pour la suite de votre parcours.\n\n"
                "Cordialement,\n"
                "L'équipe encadrante."
            ),
        },
        {
            "label": "Fin de stage – recommandation",
            "text": (
                "Bonjour,\n\n"
                "Votre stage au sein de notre entreprise s'est très bien déroulé.\n"
                "Nous serons ravis de vous recommander pour de futures opportunités si besoin.\n"
                "N'hésitez pas à nous mentionner comme référence.\n\n"
                "Cordialement,\n"
                "L'équipe encadrante."
            ),
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for item in self.DEFAULT_QUICK_REPLIES:
            label = item["label"]
            text = item["text"]

            # On évite les doublons : même label, même rôle (company)
            obj, created = QuickReply.objects.get_or_create(
                label=label,
                for_role="company",
                owner=None,
                defaults={
                    "text": text,
                    "is_global": True,
                    "is_active": True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Créé : {label}"))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"⏩ Déjà existant, ignoré : {label}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Terminé. {created_count} modèles créés, {skipped_count} ignorés."
        ))