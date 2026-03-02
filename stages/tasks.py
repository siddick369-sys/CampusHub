from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from django.db.models import F

from .models import StageOffer, Application, Notification
from .views import notify_company_offer_closed  # on réutilise ton helper


# -----------------------------------------------------------
# 1️⃣ FERMETURE AUTOMATIQUE DES OFFRES EXPIRÉES
# -----------------------------------------------------------

@shared_task(name="stages.tasks. close_expired_offers_task")
def close_expired_offers_task():
    """
    Tâche quotidienne :
    - ferme les offres dont la date limite est dépassée
    - ferme les offres ayant atteint le nombre max de candidatures
    - notifie l'entreprise
    """
    today = timezone.now().date()

    offers = StageOffer.objects.filter(
        is_active=True,
        status='published',
    )

    for offer in offers:
        was_open = offer.is_open

        # Applique _auto_update_status() via save()
        offer.save()

        if was_open and not offer.is_open:
            max_reached = (
                offer.max_applicants is not None
                and offer.applications_count >= offer.max_applicants
            )
            deadline_passed = (
                offer.application_deadline is not None
                and today > offer.application_deadline
            )

            if max_reached and deadline_passed:
                reason = "both"
            elif max_reached:
                reason = "max_applicants"
            elif deadline_passed:
                reason = "deadline"
            else:
                reason = "unknown"

            notify_company_offer_closed(offer, reason)

    return "Done"


# -----------------------------------------------------------
# 2️⃣ RAPPEL POUR LES CANDIDATURES NON CONSULTÉES
# -----------------------------------------------------------

@shared_task(name="stages.tasks.remind_unread_applications_task")
def remind_unread_applications_task():
    """
    Envoie un rappel email + notification :
    - aux entreprises
    - pour les candidatures non lues (status = submitted)
    - créées il y a X jours (ex : 3 jours)
    - pas encore rappelées (reminder_sent=False)
    """
    cutoff_days = 3
    cutoff_time = timezone.now() - timezone.timedelta(days=cutoff_days)

    applications = (
        Application.objects
        .select_related('offer', 'offer__company', 'student')
        .filter(
            status='submitted',
            created_at__lte=cutoff_time,
            reminder_sent=False,
            offer__is_active=True,
            offer__status='published',
        )
    )

    if not applications.exists():
        return "No unread applications to remind."

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

    for app in applications:
        offer = app.offer
        company = offer.company

        # Message interne simple
        notif_message = (
            f"Vous avez une candidature non traitée pour l'offre « {offer.title} ».\n\n"
            f"- Candidat : {app.student.username}\n"
            f"- Date de candidature : {app.created_at.strftime('%d/%m/%Y %H:%M')}\n"
            f"Merci de consulter cette candidature dans votre espace entreprise."
        )

        # 🔔 Notification interne
        Notification.objects.create(
            user=company,
            notif_type="new_application",
            message=notif_message,
            offer=offer,
            application=app,
        )

        # 📧 Email HTML professionnel
        if company.email:
            subject = f"Rappel : candidature non traitée pour « {offer.title} »"

            html_message = render_to_string(
                "emails/unread_application_reminder.html",
                {
                    "company": company,
                    "offer": offer,
                    "application": app,
                    "base_url": base_url,
                }
            )

            try:
                send_mail(
                    subject=subject,
                    message=notif_message,  # fallback texte
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[company.email],
                    fail_silently=True,
                    html_message=html_message,
                )
            except Exception:
                pass

        # Empêche les rappels multiples
        app.reminder_sent = True
        app.save(update_fields=["reminder_sent"])

    return f"{applications.count()} unread applications reminded."


from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from accounts.models import Profile
from stages.models import StageOffer, Application, StudentDocument
from orientation.models import OrientationResult

# tasks.py (Extrait corrigé)
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import get_connection, EmailMessage

from accounts.models import Profile
from stages.models import StageOffer, Application, StudentDocument
from orientation.models import OrientationResult

@shared_task(name="stages.tasks.send_daily_student_todo_emails_task")
def send_daily_student_todo_emails_task():
    """
    Tâche quotidienne optimisée pour l'envoi en masse.
    """
    today = timezone.now().date()
    tomorrow = today + timezone.timedelta(days=1)

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    default_from = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    # 1. Ouverture d'une seule connexion SMTP pour tout le traitement
    connection = get_connection()
    connection.open()
    
    # Liste pour stocker les objets EmailMessage avant envoi groupé
    messages_to_send = []

    # 2. Utilisation de .iterator() pour économiser la mémoire (évite de charger 10k profils)
    student_profiles = Profile.objects.select_related("user").filter(
        role="student",
        user__is_active=True,
        user__email__isnull=False
    ).iterator()

    try:
        for profile in student_profiles:
            user = profile.user
            email = user.email
            todo_lines = []

            # --- Vérifications (inchangées) ---
            
            # A) CV par défaut
            has_default_cv = StudentDocument.objects.filter(
                user=user,
                doc_type="cv",
                is_default_cv=True
            ).exists()

            if not has_default_cv:
                todo_lines.append("• Tu n’as pas encore de CV généré sur CampusHub.")

            # B) Dernière candidature
            last_application = (
                Application.objects
                .filter(student=user)
                .order_by("-created_at")
                .first()
            )

            if last_application:
                delta = timezone.now() - last_application.created_at
                days = delta.days
                if days >= 7:
                    todo_lines.append(f"• Tu n’as pas postulé à une offre depuis {days} jours.")
            else:
                todo_lines.append("• Tu n’as encore jamais postulé à une offre. Lance-toi !")

            # C) Offre qui se termine demain
            last_orientation = (
                OrientationResult.objects
                .filter(user=user)
                .order_by("-created_at")
                .first()
            )

            if last_orientation:
                suggested_tracks = last_orientation.suggested_tracks.all()
                if suggested_tracks.exists():
                    matching_offers = (
                        StageOffer.objects
                        .filter(
                            is_active=True,
                            status='published',
                            application_deadline=tomorrow,
                            related_tracks__in=suggested_tracks,
                        )
                        .order_by("-created_at")
                    )
                    # On prend juste la première pour l'exemple
                    offer = matching_offers.first()
                    if offer:
                        offer_url = f"{base_url}/stages/offers/{offer.slug}/"
                        todo_lines.append(
                            f"• Une offre correspondant à ton profil se termine demain : « {offer.title} ».\n  Voir l’offre : {offer_url}"
                        )

            # --- Construction de l'email ---
            if not todo_lines:
                continue

            subject = "CampusHub – À faire aujourd’hui"
            header = f"Bonjour {profile.full_name or user.username},\n\nVoici quelques actions importantes à faire aujourd'hui sur CampusHub :\n\n"
            footer = (
                "\n\nTu peux te connecter à ton espace : "
                f"{base_url}/stages/student/dashboard/\n\n"
                "À très vite sur CampusHub !"
            )
            body = header + "\n".join(todo_lines) + footer

            # Création de l'objet EmailMessage utilisant la connexion partagée
            email_msg = EmailMessage(
                subject,
                body,
                default_from,
                [email],
                connection=connection
            )
            messages_to_send.append(email_msg)

            # (Optionnel) Envoi par paquets de 100 pour éviter de saturer la mémoire si 10k emails
            if len(messages_to_send) >= 100:
                connection.send_messages(messages_to_send)
                messages_to_send = []

        # Envoi du reste
        if messages_to_send:
            connection.send_messages(messages_to_send)

    finally:
        # Toujours fermer la connexion
        connection.close()

    return "Daily student todo emails sent."

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q

from .models import Conversation, Message, Notification


@shared_task(name="stages.tasks.remind_conversation_messages_task")
def remind_conversation_messages_task():
    """
    Rappels intelligents sur la messagerie :
      - Rappel aux entreprises si elles ne répondent pas depuis X jours
      - Rappel aux étudiants s'ils n'ont pas lu un message important
    """
    now = timezone.now()
    company_cutoff = now - timezone.timedelta(days=2)  # X jours sans réponse
    student_cutoff = now - timezone.timedelta(days=1)  # 1 jour sans lecture

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

    conversations = (
        Conversation.objects
        .filter(is_active=True)
        .select_related("student", "company", "application__offer")
    )

    company_reminders = 0
    student_reminders = 0

    for conv in conversations:
        last_msg = (
            Message.objects
            .filter(conversation=conv)
            .order_by("-created_at")
            .first()
        )
        if not last_msg:
            continue

        # ------------------------------------------------------
        # 1️⃣ Rappel à l'entreprise :
        #     dernier message vient de l'étudiant
        #     et date d'il y a >= 2 jours
        # ------------------------------------------------------
        if (
            last_msg.sender_id == conv.student_id
            and last_msg.created_at <= company_cutoff
        ):
            if (
                conv.company_last_reminder_at is None
                or conv.company_last_reminder_at < last_msg.created_at
            ):
                student_name = getattr(conv.student.profile, "full_name", None) or conv.student.username
                offer = conv.application.offer if conv.application else None
                offer_title = offer.title if offer else "une offre"

                notif_text = (
                    f"Vous avez un message non répondu de {student_name} "
                    f"dans la conversation à propos de « {offer_title} »."
                )

                # 🔔 Notification interne
                Notification.objects.create(
                    user=conv.company,
                    notif_type="general",  # ou 'message_reminder' si tu crées ce type
                    message=notif_text,
                    offer=offer,
                    application=conv.application,
                )

                # 📧 Email à l'entreprise
                if conv.company.email:
                    subject = "CampusHub – Message non répondu d'un étudiant"
                    conversation_url = f"{base_url}/stages/messages/{conv.id}/"

                    email_body = (
                        f"Bonjour,\n\n"
                        f"Vous avez un message non répondu de {student_name} "
                        f"concernant « {offer_title} » sur CampusHub.\n\n"
                        f"Pour répondre, connectez-vous et ouvrez la conversation :\n"
                        f"{conversation_url}\n\n"
                        f"Ceci est un rappel automatique de CampusHub."
                    )

                    try:
                        send_mail(
                            subject,
                            email_body,
                            getattr(settings, "DEFAULT_FROM_EMAIL", None),
                            [conv.company.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

                conv.company_last_reminder_at = now
                conv.save(update_fields=["company_last_reminder_at"])
                company_reminders += 1

        # ------------------------------------------------------
        # 2️⃣ Rappel à l'étudiant :
        #     message important non lu de l'entreprise
        #     (entretien / rdv) depuis >= 1 jour
        # ------------------------------------------------------
        unread_important_exists = (
            Message.objects
            .filter(
                conversation=conv,
                is_read=False,
                sender=conv.company,
                created_at__lte=student_cutoff,
            )
            .filter(
                Q(text__icontains="entretien") |
                Q(text__icontains="interview") |
                Q(text__icontains="rdv") |
                Q(text__icontains="rendez-vous")
            )
            .exists()
        )

        if unread_important_exists:
            if (
                conv.student_last_reminder_at is None
                or conv.student_last_reminder_at < student_cutoff
            ):
                company_name = getattr(conv.company.profile, "company_name", None) or conv.company.username
                offer = conv.application.offer if conv.application else None
                offer_title = offer.title if offer else "une offre"

                notif_text = (
                    f"Tu as peut-être manqué un message important de {company_name} "
                    f"concernant « {offer_title} »."
                )

                # 🔔 Notification interne
                Notification.objects.create(
                    user=conv.student,
                    notif_type="general",
                    message=notif_text,
                    offer=offer,
                    application=conv.application,
                )

                # 📧 Email à l'étudiant
                if conv.student.email:
                    subject = "CampusHub – Message important non lu"
                    conversation_url = f"{base_url}/stages/messages/{conv.id}/"

                    email_body = (
                        f"Salut {conv.student.username},\n\n"
                        f"Tu as peut-être manqué un message important de {company_name} "
                        f"à propos de « {offer_title} » sur CampusHub.\n\n"
                        f"Pour le lire, connecte-toi et ouvre la conversation :\n"
                        f"{conversation_url}\n\n"
                        f"Ceci est un rappel automatique de CampusHub."
                    )

                    try:
                        send_mail(
                            subject,
                            email_body,
                            getattr(settings, "DEFAULT_FROM_EMAIL", None),
                            [conv.student.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

                conv.student_last_reminder_at = now
                conv.save(update_fields=["student_last_reminder_at"])
                student_reminders += 1

    return f"Rappels envoyés : {company_reminders} entreprises, {student_reminders} étudiants."



from celery import shared_task
from django.contrib.auth import get_user_model

from accounts.models import Profile
from accounts.utils_trust import recompute_trust_score_for_profile
from django.core.mail import mail_admins

User = get_user_model()


@shared_task(name="stages.tasks.recompute_all_trust_scores_task")
def recompute_all_trust_scores_task():
    """
    Recalcule le trust_score pour tous les profils.
    A lancer par Celery Beat (ex : chaque nuit).
    """
    profiles = Profile.objects.select_related("user").all()
    red_zone_profiles = []

    for profile in profiles:
        new_score = recompute_trust_score_for_profile(profile)
        if new_score <= 20:
            red_zone_profiles.append(profile)

    # Alerte admin si certains sont en zone rouge
    if red_zone_profiles:
        body_lines = []
        for p in red_zone_profiles:
            body_lines.append(
                f"- {p.user.username} (id={p.user.id}, email={p.user.email}) "
                f"→ trust_score={p.trust_score}"
            )

        message = (
            "Certains utilisateurs sont en zone rouge (trust_score <= 20) :\n\n"
            + "\n".join(body_lines)
        )
        mail_admins(
            subject="CampusHub – Alertes trust_score (zone rouge)",
            message=message,
            fail_silently=True,
        )

    return f"Trust scores recalculated for {profiles.count()} profiles."



from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from .models import SavedOffer, StageOffer

@shared_task(name="stages.tasks.remind_saved_offers_deadline_task")
def remind_saved_offers_deadline_task():
    """
    Envoie un email aux étudiants quand une de leurs offres sauvegardées
    se termine demain.
    """
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    default_from = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    tomorrow = timezone.localdate() + timezone.timedelta(days=1)

    saved_qs = (
        SavedOffer.objects
        .select_related("student", "offer", "offer__company")
        .filter(offer__is_active=True, offer__status="published")
        .filter(offer__application_deadline=tomorrow)
    )

    # regrouper par étudiant
    by_student = {}
    for s in saved_qs:
        user = s.student
        if not user.email:
            continue
        by_student.setdefault(user, []).append(s.offer)

    for student, offers in by_student.items():
        lines = []
        for offer in offers:
            offer_url = f"{base_url}/stages/offers/{offer.slug}/"
            lines.append(f"• {offer.title} – {offer.company.username}\n  Voir l’offre : {offer_url}")

        subject = "CampusHub – Offres sauvegardées qui se terminent demain"
        header = f"Bonjour {student.username},\n\nLes offres suivantes que tu as sauvegardées se terminent demain :\n\n"
        footer = (
            "\n\nPense à compléter tes candidatures si ce n'est pas déjà fait.\n"
            "À très vite sur CampusHub !"
        )
        message = header + "\n".join(lines) + footer

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=default_from,
                recipient_list=[student.email],
                fail_silently=True,
            )
        except Exception:
            continue

    return "Saved offers deadline reminders sent."