# incubateur/utils.py
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from .tasks import send_plain_email_task

class EmailThread(threading.Thread):
    def __init__(self, subject, message, recipient_list):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                settings.DEFAULT_FROM_EMAIL,
                self.recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            print(f"❌ Erreur d'envoi d'email (Thread): {e}")

# --- 1. NOTIFICATION ÉTUDIANT (Sans "None") ---

def envoyer_notification_resultat(participation, decision, feedback):
    """
    Prépare le contenu de l'email selon la décision (Accepté/Refusé)
    Gère les valeurs None pour éviter les trous dans le texte.
    """
    etudiant = participation.candidat
    challenge = participation.challenge
    entreprise = challenge.entreprise

    # --- LOGIQUE DE FALLBACK (Anti-None) ---
    # Si full_name est vide, on prend le username
    nom_etudiant = etudiant.full_name or etudiant.user.username or "Étudiant"
    
    # Si company_name est vide, on essaie full_name, sinon "L'entreprise"
    nom_entreprise = entreprise.company_name or entreprise.full_name or "L'entreprise partenaire"
    
    # Si le feedback est vide, on met un message par défaut
    texte_feedback = feedback if feedback and feedback.strip() else "Aucun commentaire spécifique n'a été ajouté."

    if decision == 'accepted':
        subject = f"🎉 Félicitations ! Votre solution pour {challenge.titre} a été retenue"
        message = f"""Bonjour {nom_etudiant},
        
Excellente nouvelle ! {nom_entreprise} a validé votre solution pour le challenge "{challenge.titre}".

Leur retour :
"{texte_feedback}"

L'équipe CampusHub ou l'entreprise vous contactera très prochainement pour la suite (récompense/stage).
Bravo pour votre travail !
        """
    else:
        subject = f"Retour sur votre participation au challenge {challenge.titre}"
        message = f"""Bonjour {nom_etudiant},
        
{nom_entreprise} a examiné votre solution pour le challenge "{challenge.titre}".
Malheureusement, votre proposition n'a pas été retenue cette fois-ci.

Voici leur retour pour vous aider à progresser :
"{texte_feedback}"

Ne vous découragez pas, d'autres opportunités vous attendent sur CampusHub !
        """

    # Envoi sécurisé
    if etudiant.user.email:
        from .tasks import send_plain_email_task

        send_plain_email_task.delay(
    subject,
    message,
    [etudiant.user.email]
)
    else:
        print(f"⚠️ Pas d'email pour l'étudiant {nom_etudiant}")

# --- 2. ALERTE ADMIN (Fonction demandée) ---

def send_mail_to_admin(message_text, subject_prefix="🚨 ALERTE"):
    """
    Envoie un email à tous les Superusers (Admins) du site.
    """
    # Récupère tous les emails des superutilisateurs (admins Django)
    admin_emails = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))
    
    # On filtre pour enlever les emails vides
    admin_emails = [email for email in admin_emails if email]

    if not admin_emails:
        print("⚠️ Aucun administrateur avec une adresse email trouvée.")
        return

    subject = f"{subject_prefix} - CampusHub Admin"
    
    message = f"""Bonjour Admin,

Une intervention est requise sur la plateforme.

Détails :
--------------------------------------------------
{message_text}
--------------------------------------------------

Ceci est un message automatique.
    """
    send_plain_email_task.delay(
    subject,
    message,
    admin_emails
)

    
import threading
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        # On crée aussi une version texte brut pour les boites mail anciennes
        self.text_content = strip_tags(html_content) 
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.text_content, # Version Texte
                settings.DEFAULT_FROM_EMAIL,
                self.recipient_list,
                html_message=self.html_content, # Version HTML (Importante)
                fail_silently=False,
            )
        except Exception as e:
            print(f"❌ Erreur d'envoi d'email (Thread): {e}")

# Nouvelle fonction d'aide spécifique pour la confirmation
def envoyer_email_confirmation_soumission(participation, request):
    """
    Prépare les données et lance le thread d'envoi.
    """
    etudiant = participation.candidat
    challenge = participation.challenge
    
    # 1. Préparation du contexte pour le template HTML
    context = {
        'etudiant_name': etudiant.full_name or etudiant.user.username,
        'challenge_titre': challenge.titre,
        'entreprise_name': challenge.entreprise.company_name,
        'date_soumission': participation.date_soumission.strftime("%d/%m/%Y à %H:%M"),
        # On construit l'URL absolue vers le dashboard ou le détail du challenge
        'link_dashboard': request.build_absolute_uri('/incubation/challenges/' + str(challenge.pk) + '/')
    }

    # 2. Rendu du HTML
    html_content = render_to_string('incubateur/emails/confirmation_soumission.html', context)
    subject = f"✅ Confirmation de participation : {challenge.titre}"

    # 3. Lancement du Thread
    if etudiant.user.email:
        EmailThread(subject, html_content, [etudiant.user.email]).start()
        
        
        
# incubateur/utils.py

def notifier_modification_challenge(challenge, modifications_importantes=False):
    """
    Prévient tous les candidats si le challenge change de manière critique (ex: Date limite).
    """
    if not modifications_importantes:
        return

    candidats = [p.candidat.user.email for p in challenge.participationchallenge_set.all() if p.candidat.user.email]
    
    if not candidats:
        return

    subject = f"⚠️ Modification importante : {challenge.titre}"
    message = f"""
    Bonjour,
    
    L'entreprise {challenge.entreprise.company_name} a modifié les conditions du challenge "{challenge.titre}".
    
    Nouvelle date limite : {challenge.date_limite.strftime('%d/%m/%Y')}
    
    Veuillez vérifier les détails sur la plateforme.
    
    L'équipe CampusHub
    """
    # Envoi groupé (Bcc pour la confidentialité)
    EmailThread(subject, message, candidats).start()

def notifier_suppression_challenge(challenge):
    """
    Prévient les candidats que le challenge est annulé.
    """
    candidats = [p.candidat.user.email for p in challenge.participationchallenge_set.all() if p.candidat.user.email]
    
    if not candidats:
        return

    subject = f"🛑 Annulation du challenge : {challenge.titre}"
    message = f"""
    Bonjour,
    
    Nous sommes désolés de vous informer que le challenge "{challenge.titre}" a été annulé par l'entreprise.
    
    Votre participation a été clôturée. N'hésitez pas à chercher d'autres opportunités sur CampusHub.
    
    L'équipe CampusHub
    """
    EmailThread(subject, message, candidats).start()