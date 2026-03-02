import threading
from django.conf import settings
from django.core.mail import send_mass_mail

# Assurez-vous que cette classe est définie (dans ce fichier ou importée depuis utils)
class MassEmailThread(threading.Thread):
    def __init__(self, messages):
        self.messages = messages
        threading.Thread.__init__(self)

    def run(self):
        # send_mass_mail ouvre une seule connexion pour tous les messages
        send_mass_mail(self.messages, fail_silently=True)

def notify_applicants_stage_offer_closed(offer, applicants):
    """
    Prépare les emails personnalisés pour tous les candidats
    et les envoie en arrière-plan via un Thread.
    """
    subject = f"Offre fermée : {offer.title}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    
    # Liste qui contiendra les tuples (sujet, message, envoyeur, destinataires)
    messages_to_send = []

    for user in applicants:
        if not getattr(user, "email", None):
            continue

        message_text = (
            f"Bonjour {user.username},\n\n"
            f"L'offre « {offer.title} » publiée par {offer.company.username} "
            "a été fermée par l'entreprise.\n\n"
            "Vos candidatures restent visibles dans votre espace, "
            "mais il ne sera plus possible de postuler à cette offre.\n\n"
            "Merci d'utiliser CampusHub."
        )

        # On ajoute le message à la liste d'envoi
        # Format requis par send_mass_mail : (sujet, message, de, [destinataires])
        email_data = (
            subject, 
            message_text, 
            from_email, 
            [user.email]
        )
        messages_to_send.append(email_data)

    # Si on a des emails à envoyer, on lance le thread
    if messages_to_send:
        MassEmailThread(messages_to_send).start()