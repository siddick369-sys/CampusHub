# accounts/utils_emails.py

from django.conf import settings
from django.core.mail import send_mail


def send_provider_verified_email(profile):
    """
    Envoie un email à l'utilisateur quand son profil prestataire
    vient d'être vérifié par l'admin.
    """
    user = profile.user
    if not user.email:
        return  # pas d'email, on ne fait rien

    site_name = getattr(settings, "SITE_NAME", "CampusHub")
    base_url = getattr(settings, "SITE_BASE_URL", "https://example.com")

    # 🔗 À adapter avec tes vraies pages :
    help_center_url = f"{base_url}/aide/prestataires/"
    video_url = f"{base_url}/ressources/video-devenir-prestataire/"
    testimonials_url = f"{base_url}/temoignages/prestataires/"

    subject = f"[{site_name}] Votre compte prestataire a été vérifié ✅"

    message = (
        f"Bonjour {user.first_name or user.username},\n\n"
        f"Bonne nouvelle : votre profil a été vérifié en tant que prestataire sur {site_name} ! 🎉\n\n"
        f"Vous pouvez maintenant publier des services, recevoir des commandes et commencer à travailler avec des clients.\n\n"
        f"Pour bien démarrer, voici quelques ressources utiles :\n\n"
        f"📘 Guide prestataire : {help_center_url}\n"
        f"🎥 Vidéo d'explication : {video_url}\n"
        f"💬 Témoignages d'autres prestataires : {testimonials_url}\n\n"
        f"Pensez à :\n"
        f"- compléter votre profil (photo, description, ville…)\n"
        f"- rédiger des services clairs avec des prix et délais réalistes\n"
        f"- répondre rapidement aux commandes et messages des clients\n\n"
        f"À très vite sur {site_name} !\n\n"
        f"L'équipe {site_name}"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        # On n'explose pas l'admin si l'envoi d'email échoue
        pass