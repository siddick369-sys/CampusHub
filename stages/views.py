from django.core.cache import cache
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F

from .models import CompanyFeedbacke


from .utils_notifications import notify_applicants_stage_offer_closed
from django.contrib.auth import get_user_model

from .utils_sensitive import contains_sensitive_info

from .utils_moderation import validate_content_moderation

from .utils_messages import send_new_message_notification
from .models import Conversation, Message, QuickReply

from .utils_matching import compute_matching_score
from accounts.decorators import *
from .models import StageOffer, Application, StudentDocument, Notification
from accounts.models import Profile
from .forms import StageOfferForm, ApplicationForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .utils_stats import *
from .utils_security import build_request_fingerprint
from .models import Application, StageOffer, StudentDocument, Notification
# -------------------------------------------------------------------
#  HELPERS : LETTRE DE MOTIVATION & RECOMMANDATION
# -------------------------------------------------------------------
import threading
from django.core.mail import send_mail, send_mass_mail, get_connection

class EmailThread(threading.Thread):
    """Pour envoyer un seul email en arrière-plan."""
    def __init__(self, subject, message, from_email, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.from_email = from_email
        self.recipient_list = recipient_list
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                self.from_email,
                self.recipient_list,
                fail_silently=True,
                html_message=self.html_message
            )
        except Exception as e:
            # En prod, logguez l'erreur ici
            print(f"Erreur d'envoi d'email threadé : {e}")

class MassEmailThread(threading.Thread):
    """Pour envoyer une liste d'emails en masse (optimisé avec une seule connexion)."""
    def __init__(self, messages):
        self.messages = messages
        threading.Thread.__init__(self)

    def run(self):
        try:
            # send_mass_mail ouvre une seule connexion pour tous les messages
            send_mass_mail(self.messages, fail_silently=True)
        except Exception as e:
            print(f"Erreur d'envoi de masse : {e}")


def build_motivation_letter(user, offer):
    """
    Génère une lettre de motivation structurée et personnalisée
    à partir des données du profil étudiant + de l'offre.
    L'étudiant peut ensuite la modifier avant envoi.

    Adaptée à tout type de filière (texte généraliste mais sérieux).
    """
    profile = getattr(user, 'profile', None)

    full_name = profile.full_name or user.username if profile else user.username
    city = profile.city if profile and profile.city else ""
    phone = profile.phone if profile and profile.phone else ""
    email = user.email or ""

    school = getattr(profile, 'student_school', "") if profile else ""
    level = getattr(profile, 'student_level', "") if profile else ""
    field = getattr(profile, 'student_field', "") if profile else ""

    titre_offre = offer.title
    entreprise = offer.company_name_snapshot or offer.company.username
    today = timezone.localdate()

    # On prépare des morceaux de texte dynamiques
    niveau_texte = level or "étudiant(e)"
    domaine_texte = field or "votre domaine de formation"
    ecole_texte = f" à {school}" if school else ""

    competences_techniques = offer.skills_required or "les compétences techniques développées au cours de ma formation"
    competences_plus = offer.skills_nice_to_have
    soft_skills = offer.soft_skills_required or "mon sens des responsabilités, ma capacité d’adaptation et mon esprit d’équipe"

    header_lines = [
        full_name,
        (city or "").strip(),
        (phone or "").strip(),
        (email or "").strip(),
    ]
    header = "\n".join([line for line in header_lines if line])

    intro = (
        f"{header}\n\n"
        f"{entreprise}\n\n"
        f"{city or 'Ville'}, le {today.strftime('%d/%m/%Y')}\n\n"
        f"Objet : Candidature au poste de {titre_offre}\n"
    )

    paragraphe1 = (
        "Madame, Monsieur,\n\n"
        f"Actuellement {niveau_texte.lower()} en {domaine_texte}{ecole_texte}, "
        f"je suis à la recherche d'une opportunité de {offer.get_contract_type_display().lower()} "
        f"me permettant de mettre en pratique mes connaissances et de développer de nouvelles compétences. "
        f"Votre offre pour le poste de {titre_offre} a particulièrement retenu mon attention, "
        "car elle correspond pleinement à mes aspirations académiques et professionnelles."
    )

    paragraphe2 = (
        "Au cours de mon parcours, j’ai pu acquérir des bases solides, notamment dans "
        f"{competences_techniques}. "
        "J’ai également eu l’occasion de travailler sur différents projets académiques et personnels, "
        "ce qui m’a permis de développer ma rigueur, mon autonomie et ma capacité à apprendre rapidement."
    )

    if competences_plus:
        paragraphe2 += (
            "\n\nPar ailleurs, je m’intéresse particulièrement aux aspects suivants, que vous mentionnez comme "
            "des atouts dans votre offre : "
            f"{competences_plus}. "
            "Je suis motivé(e) à approfondir ces thématiques au sein de votre structure."
        )

    paragraphe3 = (
        "Sur le plan humain, je me distingue par "
        f"{soft_skills}. "
        "Je m’investis pleinement dans les missions qui me sont confiées et je sais m’intégrer au sein d’une équipe, "
        "tout en étant capable de travailler de manière autonome lorsque cela est nécessaire."
    )

    paragraphe4 = (
        "Rejoindre votre organisation représenterait pour moi une réelle opportunité de progresser, "
        "de mieux comprendre les attentes du monde professionnel et de contribuer de manière concrète "
        "aux projets qui me seraient confiés. Je suis convaincu(e) que cette expérience constituerait "
        "une étape déterminante dans la construction de mon projet professionnel."
    )

    conclusion = (
        "Je me tiens bien entendu à votre disposition pour un entretien, durant lequel je pourrais vous exposer "
        "plus en détail ma motivation et répondre à vos questions.\n\n"
        "Veuillez agréer, Madame, Monsieur, l’expression de mes salutations distinguées.\n\n"
        f"{full_name}"
    )

    return "\n\n".join([intro, paragraphe1, paragraphe2, paragraphe3, paragraphe4, conclusion])
from .utils_security import (
    is_too_big,
    is_extension_allowed,
    scan_attachment_for_sensitive_info,
    detect_mime,
)

def build_recommendation_template(user):
    """
    Génère un modèle de lettre de recommandation qu’un enseignant
    ou une école peut utiliser, en le personnalisant et en le signant.

    Le texte reste généraliste pour être valable pour toutes les filières.
    """
    profile = getattr(user, 'profile', None)

    full_name = profile.full_name or user.username if profile else user.username
    school = getattr(profile, 'student_school', "") if profile else ""
    level = getattr(profile, 'student_level', "") if profile else ""
    field = getattr(profile, 'student_field', "") if profile else ""
    today = timezone.localdate()

    niveau_texte = level or "étudiant(e)"
    domaine_texte = field or "son domaine de formation"
    ecole_texte = f" au sein de {school}" if school else ""

    intro = (
        "À qui de droit,\n\n"
        f"Je soussigné(e), [NOM DU SIGNATAIRE], [FONCTION DU SIGNATAIRE]{ecole_texte}, "
        f"certifie que {full_name}, {niveau_texte.lower()} en {domaine_texte}, "
        "a suivi avec sérieux et assiduité les enseignements qui lui ont été dispensés."
    )

    paragraphe1 = (
        f"Au cours de la période durant laquelle j’ai pu encadrer {full_name}, "
        "j’ai pu constater son implication, sa curiosité intellectuelle et sa capacité à progresser. "
        "Il/Elle participe activement aux activités proposées, pose des questions pertinentes et montre un réel intérêt "
        "pour les notions abordées, en particulier lorsqu’elles sont en lien avec son projet professionnel."
    )

    paragraphe2 = (
        f"{full_name} se distingue également par des qualités humaines appréciables : "
        "respect des consignes, esprit d’équipe, sens des responsabilités et sérieux dans le travail. "
        "Il/Elle sait collaborer avec ses camarades, tout en étant capable de travailler de manière autonome "
        "lorsque cela est nécessaire."
    )

    paragraphe3 = (
        "Dans le cadre des projets et évaluations, {nom} a démontré une capacité à analyser des problèmes, "
        "à proposer des solutions pertinentes et à s’investir jusqu’à l’aboutissement des tâches qui lui sont confiées. "
        "Son attitude générale laisse entrevoir un fort potentiel de développement dans un environnement professionnel."
    ).replace("{nom}", full_name)

    paragraphe4 = (
        "C’est pourquoi je recommande vivement {nom} pour tout stage, alternance ou premier emploi "
        "en adéquation avec son profil et son projet. Je suis convaincu(e) qu’il/elle saura s’adapter aux exigences du "
        "milieu professionnel et apporter une contribution positive à l’équipe qui l’accueillera."
    ).replace("{nom}", full_name)

    conclusion = (
        f"Fait à [VILLE], le {today.strftime('%d/%m/%Y')}.\n\n"
        "[Nom et prénom du signataire]\n"
        "[Fonction]\n"
        f"{school if school else '[Établissement]'}\n"
        "[Signature et cachet, le cas échéant]"
    )

    return "\n\n".join([intro, paragraphe1, paragraphe2, paragraphe3, paragraphe4, conclusion])


# -------------------------------------------------------------------
#  VUES CÔTÉ ÉTUDIANT
# -------------------------------------------------------------------
# stages/utils.py
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from orientation.models import OrientationResult
from .models import Application, Notification


def notify_students_for_new_offer(offer):
    related_tracks = offer.related_tracks.all()
    if not related_tracks.exists():
        return

    # Optimisation SQL : select_related pour éviter de requêter le user à chaque fois
    results = (
        OrientationResult.objects
        .select_related('user', 'user__profile')
        .filter(suggested_tracks__in=related_tracks)
        .distinct()
    )

    # CORRECTION URL
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    offer_url = f"{base_url}/stages/offers/{offer.slug}/"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    
    messages_to_send = []

    for result in results:
        student = result.user
        if not student.is_active or not student.email:
            continue

        profile = getattr(student, "profile", None)
        if profile and getattr(profile, "role", None) != "student":
            continue
        
        if hasattr(profile, "receive_orientation_alerts") and not profile.receive_orientation_alerts:
            continue

        # Vérifier si déjà candidat
        if Application.objects.filter(offer=offer, student=student).exists():
            continue

        message_text = (
            f"Bonjour {student.username},\n\n"
            f"Une nouvelle offre correspond à votre profil d'orientation :\n"
            f"- Offre : {offer.title}\n"
            f"- Entreprise : {offer.company.username}\n\n"
            f"Consultez les détails et postulez ici :\n{offer_url}\n\n"
            f"Cordialement,\nL'équipe CampusHub"
        )

        # Création notif interne
        Notification.objects.create(
            user=student,
            notif_type="general",
            message=message_text,
            offer=offer,
            application=None,
        )

        # Préparation de l'email pour l'envoi groupé
        # Format send_mass_mail : (sujet, message, expediteur, [destinataires])
        email_data = (
            f"Nouvelle offre adaptée : {offer.title}",
            message_text,
            from_email,
            [student.email]
        )
        messages_to_send.append(email_data)

    # Envoi asynchrone global
    if messages_to_send:
        MassEmailThread(messages_to_send).start()
    
            
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.core.files.base import ContentFile
from django.contrib import messages

from accounts.decorators import student_required
from orientation.models import OrientationResult
from .models import Application, StudentDocument
from .utils_pdf import render_html_to_pdf_bytes

from django.contrib import messages
from accounts.services import UsageManager
from django.urls import reverse

@student_required
@profile_completion_required
def generate_and_save_cv_view(request):
    """
    Génère un CV PDF à partir du profil + orientation + candidatures
    et l'enregistre dans StudentDocument comme CV par défaut.
    Renvoie aussi le PDF en téléchargement.
    """
    user = request.user
    
    # 1. Vérification du QUOTA via UsageManager
    if not UsageManager.is_action_allowed(user, 'cv_ia'):
        messages.warning(request, "Quota hebdomadaire/mensuel de génération de CV atteint.")
        # On redirige vers une page d'initiation de paiement pour CETTE action
        # Le prix est de 500 FCFA pour un CV IA supplémentaire
        return redirect(f"{reverse('payments:initiate_payment')}?action=cv_ia&amount=500&method=mobile_money")

    user.refresh_from_db()
    
    # On s'assure d'avoir le profil le plus récent
    profile = Profile.objects.get(user=user)
    profile.refresh_from_db()

    if not profile or profile.role != "student":
        return HttpResponse("Cette fonctionnalité est réservée aux étudiants.", status=403)

    # Dernier résultat d’orientation
    last_orientation = (
        OrientationResult.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    # Quelques candidatures récentes (pour enrichir le CV)
    applications = (
        Application.objects
        .select_related("offer", "offer__company")
        .filter(student=user)
        .order_by("-created_at")[:5]
    )

    context = {
        "user": user,
        "profile": profile,
        "last_orientation": last_orientation,
        "applications": applications,
    }

    pdf_bytes = render_html_to_pdf_bytes("stages/cv_template.html", context)
    if pdf_bytes is None:
        return HttpResponse("Erreur lors de la génération du CV.", status=500)

    filename = f"CV_{user.username}.pdf"

    # Désactiver l'ancien CV par défaut
    StudentDocument.objects.filter(
        user=user,
        doc_type="cv",
        is_default_cv=True
    ).update(is_default_cv=False)

    # Créer un nouveau StudentDocument
    doc = StudentDocument.objects.create(
        user=user,
        title="CV généré automatiquement",
        doc_type="cv",
        language="Français",
        description="CV généré automatiquement à partir du profil CampusHub.",
        is_default_cv=True,
        is_public=False,
    )
    doc.file.save(filename, ContentFile(pdf_bytes))
    doc.save()

    messages.success(request, "Votre CV a été généré et enregistré comme CV par défaut.")
    
    # incrémenter le quota
    UsageManager.increment_usage(user, 'cv_ia')

    # Renvoyer le PDF pour téléchargement
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
from django.db.models import Q
from django.contrib import messages
from accounts.decorators import student_required
from .models import StageOffer, JobSearchAlert
@student_required

def offer_list_view(request):
    """
    Liste des offres pour les étudiants, avec recherche avancée :
      - q (mot-clé : titre, description, compétences, entreprise…)
      - ville / pays
      - type de contrat
      - mode (remote/onsite/hybrid)
      - niveau d'expérience
      - salaire min / max
      - durée min / max
      - uniquement offres rémunérées
      - niveau requis (texte libre)
      - exigences de langue
      - filière (related_tracks)

    Ne montre que les offres publiées et actives.

    Si aucune offre ne correspond et que l'utilisateur est un étudiant connecté
    ET qu'au moins q / city / contract / location est renseigné,
    on enregistre une alerte de recherche (logique existante conservée).
    """
    offers = StageOffer.objects.filter(
        is_active=True,
        status='published',
    )

    # --------- Récupération des filtres (anciens + nouveaux) ---------
    q = (request.GET.get('q') or "").strip()
    city = (request.GET.get('city') or "").strip()
    contract_type = (request.GET.get('contract') or "").strip()
    location_type = (request.GET.get('location') or "").strip()

    # 🔥 nouveaux filtres
    country = (request.GET.get('country') or "").strip()
    experience_level = (request.GET.get('experience') or "").strip()
    track_id = (request.GET.get('track') or "").strip()

    min_salary = (request.GET.get('min_salary') or "").strip()
    max_salary = (request.GET.get('max_salary') or "").strip()
    duration_min = (request.GET.get('duration_min') or "").strip()
    duration_max = (request.GET.get('duration_max') or "").strip()

    paid_only = request.GET.get('paid_only') == "1"
    required_level = (request.GET.get('required_level') or "").strip()
    language = (request.GET.get('language') or "").strip()

    # --------- Filtres existants ---------
    if q:
        offers = offers.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(skills_required__icontains=q) |
            Q(company_name_snapshot__icontains=q)
        )

    if city:
        offers = offers.filter(location_city__icontains=city)

    if contract_type:
        offers = offers.filter(contract_type=contract_type)

    if location_type:
        offers = offers.filter(location_type=location_type)

    # --------- Nouveaux filtres avancés ---------

    # Pays
    if country:
        offers = offers.filter(location_country__icontains=country)

    # Niveau d'expérience
    if experience_level:
        offers = offers.filter(experience_level=experience_level)

    # Filière (Track lié à l’offre)
    if track_id:
        offers = offers.filter(related_tracks__id=track_id)

    # Salaire
    if min_salary.isdigit():
        min_s = int(min_salary)
        offers = offers.filter(
            Q(salary_min__gte=min_s) | Q(salary_max__gte=min_s)
        )

    if max_salary.isdigit():
        max_s = int(max_salary)
        offers = offers.filter(
            Q(salary_min__lte=max_s) | Q(salary_max__lte=max_s)
        )

    # Durée en mois
    if duration_min.isdigit():
        offers = offers.filter(duration_months__gte=int(duration_min))

    if duration_max.isdigit():
        offers = offers.filter(duration_months__lte=int(duration_max))

    # Uniquement offres rémunérées
    if paid_only:
        offers = offers.filter(is_paid=True)

    # Niveau requis (texte libre, ex : Bac+2, Licence 3)
    if required_level:
        offers = offers.filter(required_level__icontains=required_level)

    # Langues requises
    if language:
        offers = offers.filter(language_requirements__icontains=language)

    offers = offers.order_by('-created_at').distinct()

    # 📨 LOGIQUE D’ALERTE : on NE TOUCHE PAS (comme tu l’avais)
    if not offers.exists() and (q or city or contract_type or location_type):
        user = request.user
        profile = getattr(user, "profile", None)
        if profile and profile.role == "student":
            from accounts.services import UsageManager
            if UsageManager.is_action_allowed(request.user, 'search_alerts_count'):
                alert, created = JobSearchAlert.objects.get_or_create(
                    student=user,
                    q=q or None,
                    city=city or None,
                    contract_type=contract_type or None,
                    location_type=location_type or None,
                    defaults={"is_active": True},
                )
                if created:
                    messages.info(
                        request,
                        "Aucune offre ne correspond pour l’instant. "
                        "Nous vous enverrons un email si une offre similaire est publiée."
                    )
            else:
                messages.warning(request, "Impossible de créer l'alerte de recherche : quota atteint.")

    # Pour alimenter les <select> dans le template
    contract_choices = StageOffer._meta.get_field('contract_type').choices
    location_choices = StageOffer._meta.get_field('location_type').choices
    experience_choices = StageOffer._meta.get_field('experience_level').choices

    context = {
        'offers': offers,

        # anciens contextes (pour ne rien casser)
        'q': q,
        'city': city,
        'contract_type': contract_type,
        'location_type': location_type,

        # nouveaux filtres regroupés
        'filters': {
            'q': q,
            'city': city,
            'country': country,
            'contract_type': contract_type,
            'location_type': location_type,
            'experience_level': experience_level,
            'track_id': track_id,
            'min_salary': min_salary,
            'max_salary': max_salary,
            'duration_min': duration_min,
            'duration_max': duration_max,
            'paid_only': paid_only,
            'required_level': required_level,
            'language': language,
        },
        'contract_choices': contract_choices,
        'location_choices': location_choices,
        'experience_choices': experience_choices,
    }
    return render(request, 'stages/offer_list.html', context)

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import JobSearchAlert
from django.utils import timezone
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings

from .models import JobSearchAlert, StageOffer


def normalize_city(value):
    """
    Normalise une ville pour faciliter la comparaison.
    Ex : "Douala, Cameroun" -> "douala-cameroun"
    """
    return slugify((value or "").strip())


def notify_students_for_search_alerts(offer: StageOffer):
    """
    Parcourt toutes les JobSearchAlert actives et envoie un email aux étudiants
    dont la recherche matche la nouvelle offre.
    """
    alerts = (
        JobSearchAlert.objects
        .select_related("student")
        .filter(is_active=True)
    )

    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
    offer_url = f"{base_url}/stages/offers/{offer.slug}/"
    from_email = getattr(settings,"DEFAULT_FROM_EMAIL",None)

    now = timezone.now()
    messages_to_send = []

    for alert in alerts:
        student = alert.student
        if not student.is_active or not student.email:
            continue

        profile = getattr(student, "profile", None)
        if profile and getattr(profile, "role", None) != "student":
            continue

        matches = True

        # --- Matching mot-clé ---
        if alert.q:
            q = alert.q.lower()
            text = " ".join([
                offer.title or "",
                offer.description or "",
                offer.skills_required or "",
            ]).lower()
            if q not in text:
                matches = False

        # --- Matching ville (version plus souple) ---
        if matches and alert.city:
            alert_city = normalize_city(alert.city)
            offer_city = normalize_city(offer.location_city)

            # On compare seulement le "mot principal" (ex: "douala")
            if alert_city and offer_city:
                alert_main = alert_city.split("-")[0]  # "douala-cameroun" -> "douala"
                if alert_main not in offer_city:
                    matches = False

        # --- Matching type de contrat ---
        if matches and alert.contract_type:
            if alert.contract_type != offer.contract_type:
                matches = False

        # --- Matching mode (remote/onsite/hybrid) ---
        if matches and alert.location_type:
            if alert.location_type != offer.location_type:
                matches = False

        if not matches:
            continue
        
        
        subject = "Une nouvelle offre correspond à votre recherche"
        message = (
                f"Bonjour {student.username},\n\n"
                f"Une nouvelle opportunité correspondant à vos critères :\n"
                f"- Offre : {offer.title}\n"
                f"- Entreprise : {offer.company.username}\n\n"
                f"Lien : {offer_url}\n\n"
                f"L'équipe CampusHub"
            )

            # Ajout à la liste d'envoi
        email_data = (subject, message, from_email, [student.email])
        messages_to_send.append(email_data)

        alert.last_matched_at = now
        alert.save(update_fields=["last_matched_at"])

    # Envoi asynchrone
    if messages_to_send:
        MassEmailThread(messages_to_send).start()


        alert.last_matched_at = now
        alert.save(update_fields=["last_matched_at"])

@student_required
@profile_completion_required
def offer_detail_view(request, slug):
    """
    Détail d'une offre.
    Incrémente views_count.
    """
    offer = get_object_or_404(
        StageOffer,
        slug=slug,
        is_active=True,
        status='published',
    )
    stats = get_offer_stats(offer)
    matching = None
    if hasattr(request.user, "profile") and request.user.profile.role == "student":
        matching = compute_matching_score(request.user, offer)
    

    # Incrémenter le compteur de vues
    StageOffer.objects.filter(pk=offer.pk).update(
        views_count=F('views_count') + 1
    )
    offer.refresh_from_db()

    already_applied = Application.objects.filter(
        offer=offer,
        student=request.user
    ).exists()
    similar_offers = StageOffer.objects.filter(
    contract_type=offer.contract_type).exclude(id=offer.id)[:3]
    can_leave_review = False
    if request.user.is_authenticated:
        # On vérifie seulement s'il a déjà laissé un avis sur CETTE offre
        already_reviewed = StageReview.objects.filter(
            offer=offer, 
            student=request.user
        ).exists()
        
        if not already_reviewed:
            can_leave_review = True
    # Débogage : Si le bouton ne s'affiche toujours pas, décommente la ligne suivante
    # print(f"DEBUG: App: {user_application}, Can Review: {can_leave_review}")

    context = {
        'offer': offer,
        'already_applied': already_applied,
        'stats':stats,
        'matching': matching,
        'similar_offers': similar_offers,
        'can_leave_review': can_leave_review,# Utile pour l'ID dans le bouton
    }
    return render(request, 'stages/offer_detail.html', context)


from accounts.decorators import student_required

@student_required
def student_matching_offers_view(request):
    """
    Liste les offres actives, triées par score de matching décroissant
    pour l'étudiant connecté.
    """
    offers = StageOffer.objects.filter(
        is_active=True,
        status="published",
    ).select_related("company")

    offers_with_scores = []
    for offer in offers:
        m = compute_matching_score(request.user, offer)
        if m["score"] is not None:
            offers_with_scores.append({
                "offer": offer,
                "matching": m,
            })

    # Trier par score descendant
    offers_with_scores.sort(key=lambda x: x["matching"]["score"], reverse=True)

    return render(request, "stages/student_matching_offers.html", {
        "offers_with_scores": offers_with_scores,
    })
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from accounts.decorators import student_required
from .models import StageOffer, Application, StudentDocument, Notification
from .forms import ApplicationForm  # si tu as ce helper

from django.contrib import messages
from django.shortcuts import redirect
from stages.models import Application
from datetime import datetime

@student_required
@profile_completion_required
def apply_to_offer_view(request, slug):
    sub = getattr(request.user, "subscription", None)

    if not sub or not sub.is_active:
        messages.error(request, "Tu dois avoir un abonnement actif pour postuler.")
        return redirect("subscription_plans")

    # Vérifie la limite de candidatures mensuelles
    month_apps = Application.objects.filter(student=request.user, created_at__month=datetime.now().month).count()
    if month_apps >= sub.plan.max_applications:
        messages.warning(request, "Tu as atteint ta limite de candidatures pour ce mois.")
        return redirect("subscription_plans")

    """
    Permet à un étudiant de postuler.
    Vérifie : offre active, publiée, pas expirée, pas déjà candidat.
    Pré-remplit la lettre de motivation avec un modèle personnalisé.
    Gère aussi l'auto-fermeture de l'offre si max candidatures atteint.
    """
    offer = get_object_or_404(
        StageOffer,
        slug=slug,
        is_active=True,
        status='published',
    )

    # 🔒 Vérifier que l'offre est encore ouverte
    if not offer.is_open:
        messages.error(request, "Vous ne pouvez plus postuler pour cette offre.")
        return redirect('offer_detail', slug=slug)
    
    
    fingerprint = build_request_fingerprint(request)

    # 🔒 Bloquer si ce même device a déjà postulé à cette offre
    if Application.objects.filter(
        offer=offer,
        applicant_fingerprint=fingerprint
    ).exists():
        messages.error(
            request,
            "Un compte utilisant cet appareil a déjà postulé à cette offre."
        )
        return redirect('offer_detail', slug=slug)

    # Déjà candidat ?
    if Application.objects.filter(offer=offer, student=request.user).exists():
        messages.info(request, "Vous avez déjà postulé à cette offre.")
        return redirect('offer_detail', slug=slug)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            was_open = offer.is_open  # état avant création

            # On ne sauvegarde pas encore en base
            application = form.save(commit=False)

            # ✅ TOUJOURS renseigner ces champs
            application.offer = offer
            application.student = request.user
            application.status = 'submitted'
            application.status_changed_at = timezone.now()

            # Si aucun CV choisi, on prend le CV par défaut
            if not application.cv:
                default_cv = StudentDocument.objects.filter(
                    user=request.user,
                    doc_type="cv",
                    is_default_cv=True
                ).first()
                if default_cv:
                    application.cv = default_cv
                # sinon on laisse vide si ton modèle autorise cv null/blank

            application.save()

            # 🔔 Notification pour l'entreprise : nouvelle candidature
            Notification.objects.create(
                user=offer.company,
                notif_type='new_application',
                message=(
                    f"{request.user.username} a postulé à votre offre « {offer.title} »."
                ),
                offer=offer,
                application=application,
            )

            # Incrémenter le compteur de candidatures de l'offre
            offer.applications_count += 1
            offer.save(update_fields=['applications_count'])

            # Vérifier si l'offre vient de se fermer
            if was_open and not offer.is_open:
                today = timezone.now().date()
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

            messages.success(request, "Votre candidature a été envoyée.")
            return redirect('student_applications')
    else:
        # Pré-remplir la lettre de motivation
        initial = {
            'motivation_letter': build_motivation_letter(request.user, offer)
        }
        form = ApplicationForm(user=request.user, initial=initial)

    return render(request, 'stages/apply.html', {
        'offer': offer,
        'form': form
    })

from django.contrib.auth.decorators import login_required
from accounts.decorators import student_required
from django.shortcuts import render, redirect

from .models import StudentDocument
from .forms import StudentDocumentForm


@student_required
@profile_completion_required
def student_documents_list_view(request):
    docs = StudentDocument.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "stages/student_documents_list.html", {"docs": docs})

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from accounts.decorators import student_required
from .models import StudentDocument


@student_required
@profile_completion_required
def student_document_delete_view(request, pk):
    """
    Permet à un étudiant de supprimer l'un de ses documents (CV, portfolio, etc.).
    Sécurisé : on vérifie que le document appartient bien à l'utilisateur.
    """
    doc = get_object_or_404(StudentDocument, pk=pk, user=request.user)

    if request.method == "POST":
        # On supprime aussi le fichier du disque
        if doc.file:
            doc.file.delete(save=False)

        doc.delete()
        messages.success(request, "Document supprimé avec succès.")
        return redirect("student_documents_list")

    # GET -> page de confirmation
    return render(request, "stages/student_document_confirm_delete.html", {"doc": doc})

# stages/views.py
@student_required
@profile_completion_required
def student_document_upload_view(request):
    if request.method == "POST":
        form = StudentDocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Document ajouté avec succès.")
            return redirect("student_documents_list")
    else:
        form = StudentDocumentForm(user=request.user)

    return render(request, "stages/student_document_upload.html", {"form": form})
from accounts.decorators import student_required
from .models import StudentDocument

@student_required
def student_document_download_view(request, pk):
    """
    Téléchargement sécurisé d’un document étudiant.
    - Vérifie que le document appartient bien à l'utilisateur connecté.
    - Gère les cas où le fichier n'existe plus.
    """
    doc = get_object_or_404(StudentDocument, pk=pk, user=request.user)

    # Pas de fichier associé → on redirige
    if not doc.file:
        messages.error(request, "Ce document n'a pas de fichier à télécharger.")
        return redirect("student_documents_list")

    # Essayer d'ouvrir le fichier
    try:
        file_handle = doc.file.open("rb")
    except FileNotFoundError:
        messages.error(request, "Fichier introuvable sur le serveur.")
        return redirect("student_documents_list")

    # Nom de fichier propre
    filename = doc.title or os.path.basename(doc.file.name)

    # Réponse de téléchargement
    response = FileResponse(file_handle, as_attachment=True, filename=filename)
    return response
def notify_company_offer_closed(offer, reason: str = "unknown"):
    """
    Crée une Notification pour l'entreprise + envoie un email HTML
    quand l'offre est automatiquement clôturée (max candidatures ou date limite).
    """
    
    base_url = getattr(settings,"SITE_BASE_URL","http://localhost:8000")
    company = offer.company

    if reason == "max_applicants":
        reason_text = "le nombre maximal de candidatures défini pour cette offre a été atteint."
    elif reason == "deadline":
        reason_text = "la date limite de candidature est dépassée."
    elif reason == "both":
        reason_text = "la date limite est dépassée et le nombre maximal de candidatures a été atteint."
    else:
        reason_text = "l'offre est close."

    message = (
        f"Bonjour {company.username},\n\n"
        f"Votre offre « {offer.title} » a été clôturée.\nMotif : {reason_text}\n"
    )

    Notification.objects.create(
        user=company,
        notif_type='general',
        message=message,
        offer=offer,
    )

    if company.email:
        subject = f"Clôture de votre offre « {offer.title} »"
        
        # Si vous utilisez un template HTML
        html_message = render_to_string('emails/offer_closed.html', {
            'company': company, 'offer': offer, 'reason_text': reason_text, 'base_url': base_url
        })

        # Envoi ASYNCHRONE
        EmailThread(
            subject, 
            message, 
            getattr(settings, 'DEFAULT_FROM_EMAIL', None), 
            [company.email], 
            html_message=html_message
        ).start()


@student_required
@profile_completion_required
def student_applications_view(request):
    """
    Liste des candidatures de l'étudiant, avec statut, dates, etc.
    """
    applications = (
        Application.objects
        .filter(student=request.user)
        .select_related('offer')
        .order_by('-created_at')
    )
    reviewed_app_ids = set(
        StageReview.objects.filter(student=request.user).values_list("application_id", flat=True)
    )

    for app in applications:
        app.can_review = (app.status == "accepted" and app.id not in reviewed_app_ids)

    return render(request, 'stages/student_applications.html', {'applications': applications})


@student_required
def withdraw_application_view(request, pk):
    """
    Permet à l'étudiant de retirer sa candidature.
    """
    application = get_object_or_404(
        Application,
        pk=pk,
        student=request.user
    )
    if application.is_withdrawn:
        messages.info(request, "Cette candidature a déjà été retirée.")
        return redirect('student_applications')
    if request.method == 'POST':
        application.is_withdrawn = True
        application.status = 'withdrawn'
        application.withdrawn_at = timezone.now()
        application.status_changed_at = timezone.now()
        application.delete()
        messages.success(request, "Votre candidature a été retirée.")
        return redirect('student_applications')
    return render(request, 'stages/withdraw_confirm.html', {'application': application})

def send_application_status_notification(application, old_status, new_status):
    """
    Crée une Notification + envoie un email HTML au candidat
    quand le statut de sa candidature change.
    Gère : viewed, shortlisted, accepted, rejected.
    """
    base_url = getattr(settings,"SITE_BASE-URL","http://localhost:8000")
    student = application.student
    offer = application.offer
    if not student:
        return
    has_email = bool(student.email)
    status_labels = {
        'submitted': "envoyée",
        'viewed': "consultée",
        'shortlisted': "pré-sélectionnée",
        'rejected': "refusée",
        'accepted': "acceptée",
    }
    status_label = status_labels.get(new_status, new_status)
    statuses_to_notify = ['viewed', 'shortlisted', 'accepted', 'rejected']
    if new_status not in statuses_to_notify:
        return
    base_message = (
        f"Le statut de votre candidature pour « {offer.title} » "
        f"est maintenant : {status_label}."
    )
    if new_status == 'viewed':
        extra = "L'entreprise a consulté votre profil."
    elif new_status == 'shortlisted':
        extra = "Vous avez été pré-sélectionné(e) pour la suite du processus."
    elif new_status == 'accepted':
        extra = "Félicitations ! Votre candidature a été acceptée. L'entreprise pourra vous contacter pour organiser la suite."
    elif new_status == 'rejected':
        extra = "Votre candidature n'a pas été retenue. Ne vous découragez pas et continuez à postuler."
    else:
        extra = ""
    full_message = base_message
    if extra:
        full_message += "\n\n" + extra
    # 🔔 Notification interne (texte brut pour ton site)
    Notification.objects.create(
        user=student,
        notif_type='status_update',
        message=full_message,
        offer=offer,
        application=application,
    )
    if has_email:
        subject = f"Mise à jour de votre candidature : {status_label.capitalize()}"

        # 💌 Version HTML (rendu avec un template Django)
        html_message = render_to_string(
            'emails/application_status_update.html',
            {
                'student': student,
                'offer': offer,
                'application': application,
                'status_label': status_label,
                'extra': extra,
                'base_url':base_url
            },
        )
        try:
            send_mail(
                subject=subject,
                message=full_message,  # version texte (fallback)
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[student.email],
                fail_silently=True,
                html_message=html_message,
            )
        except Exception:
            pass
from django.db.models import Count
from orientation.models import OrientationResult, Track
from accounts.decorators import student_required
from .models import StageOffer
from django.shortcuts import render
@premium_required
@student_required
@profile_completion_required
def recommended_offers_view(request):
    """
    Recommande des offres de stage en fonction
    du dernier résultat d’orientation de l’étudiant.
    """
    # Base : uniquement les offres publiées et actives
    base_qs = StageOffer.objects.filter(
        is_active=True,
        status='published',
    )
    last_result = (
        OrientationResult.objects
        .filter(user=request.user)
        .order_by('-created_at')
        .first()
    )
    recommendations = []
    if last_result and last_result.scores_data:
        # 1) Récupérer les scores par filière
        track_scores_raw = (last_result.scores_data or {}).get("tracks", {}) or {}
        # Clefs peuvent être str ou int, on normalise en int
        track_scores = {}
        for k, v in track_scores_raw.items():
            try:
                track_id = int(k)
            except (TypeError, ValueError):
                continue
            track_scores[track_id] = v or 0
        if track_scores:
            # 2) Trier les filières par score décroissant
            sorted_track_ids = sorted(
                track_scores.keys(),
                key=lambda tid: track_scores[tid],
                reverse=True
            )
            # On limite aux 5 filières les plus fortes
            top_track_ids = sorted_track_ids[:5]
            top_tracks = Track.objects.filter(id__in=top_track_ids)
            # 3) Chercher les offres liées à ces filières
            offers = (
                base_qs.filter(related_tracks__in=top_tracks)
                .distinct()
                .annotate(num_tracks=Count('related_tracks'))
            )
            # 4) Calculer un score de recommandation pour chaque offre
            #    en additionnant les scores des filières liées à l'offre
            for offer in offers:
                offer_track_ids = list(
                    offer.related_tracks.values_list('id', flat=True)
                )
                score = sum(track_scores.get(tid, 0) for tid in offer_track_ids)
                recommendations.append((offer, score))

            # 5) Trier les offres par score décroissant
            recommendations.sort(key=lambda x: x[1], reverse=True)

    # Si pas de résultat d’orientation ou pas de recommandation, fallback simple
    if not recommendations:
        fallback_offers = base_qs.order_by('-created_at')[:10]
        recommendations = [(offer, 0) for offer in fallback_offers]

    context = {
        "recommendations": recommendations,
        "last_orientation_result": last_result,
    }
    return render(request, "stages/recommended_offers.html", context)
@premium_required
@student_required
@profile_completion_required
def recommendation_template_view(request):
    """
    Affiche un modèle de lettre de recommandation
    que l'étudiant peut transmettre à un enseignant / une école.
    """
    text = build_recommendation_template(request.user)
    return render(request, 'stages/recommendation_template.html', {'text': text})
 

# -------------------------------------------------------------------
#  NOTIFICATIONS
# -------------------------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Notification

@login_required
def notifications_list_view(request):
    """
    Liste toutes les notifications de l'utilisateur.
    Marque les non lues comme lues.
    """
    notifications = (
        Notification.objects
        .filter(user=request.user)
        .order_by('-created_at')
    )
    unread_count = notifications.filter(is_read=False).count()
    notifications.filter(is_read=False).update(is_read=True)
    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    return render(request, "stages/notifications_list.html", context)
# -------------------------------------------------------------------
#  VUES CÔTÉ ENTREPRISE
# -------------------------------------------------------------------
@company_required
def company_offers_view(request):
    """
    Liste des offres créées par l'entreprise.
    """
    offers = StageOffer.objects.filter(company=request.user).order_by('-created_at')
    return render(request, 'stages/company_offers.html', {'offers': offers})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import company_required
from .models import StageOffer
from .forms import StageOfferForm

@company_subscription_required
@company_required
@profile_completion_required
def company_offer_create_view(request):
    profile = request.user.profile
    # 🚫 Entreprise non vérifiée → pas d'accès à la création d'offre
    if not profile.company_verified:
        messages.error(
            request,
            "Votre entreprise doit être vérifiée pour publier des offres sur CampusHub."
        )
        return redirect("company_verification_request")  # vue qu’on a faite pour envoyer les docs
    """
    Création d'une nouvelle offre par une entreprise.
    """
    if request.method == 'POST':
        form = StageOfferForm(request.POST)
        if form.is_valid():
            # --- Vérification Quota ---
            from accounts.services import UsageManager
            if not UsageManager.is_action_allowed(request.user, 'offer_publication'):
                messages.error(request, "Désolé, vous avez atteint votre quota mensuel de publication pour votre plan actuel.")
                return redirect('company_offers')

            offer = form.save(commit=False)
            offer.company = request.user

            # si status = published -> active
            offer.is_active = (offer.status == 'published')

            offer.save()
            
            # Incrémenter l'usage
            UsageManager.increment_usage(request.user, 'offer_publication')
            
            form.save_m2m()
            notify_students_for_new_offer(offer)
            notify_students_for_search_alerts(offer)
            messages.success(request, "Offre créée avec succès.")
            return redirect('company_offers')
        else:
            # DEBUG : voir les erreurs dans la console pour comprendre si ça casse
            print("ERREURS FORMULAIRE OFFRE :", form.errors)
    else:
        form = StageOfferForm()
    return render(request, 'stages/company_offer_form.html', {'form': form})
@company_required
def company_offer_edit_view(request, slug):
    profile = request.user.profile
    # 🚫 Entreprise non vérifiée → pas d'accès à la création d'offre
    if not profile.company_verified:
        messages.error(
            request,
            "Votre entreprise doit être vérifiée pour publier des offres sur CampusHub."
        )
        return redirect("company_verification_request")  # vue qu’on a faite pour envoyer les docs
    offer = get_object_or_404(StageOffer, slug=slug, company=request.user)

    if request.method == 'POST':
        form = StageOfferForm(request.POST, instance=offer)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.is_active = (offer.status == 'published')
            offer.save()
            form.save_m2m()
            messages.success(request, "Offre mise à jour.")
            return redirect('company_offers')
    else:
        form = StageOfferForm(instance=offer)

    return render(request, 'stages/company_offer_form.html', {'form': form, 'offer': offer})
@company_required
@profile_completion_required
def company_application_update_status_view(request, pk):
    """
    Permet à l'entreprise de changer le statut d'une candidature
    (shortlisted / accepted / rejected / etc.) + rating + note.
    Affiche aussi les documents publics (portfolio...) de l'étudiant.
    """
    application = get_object_or_404(
        Application,
        pk=pk,
        offer__company=request.user
    )

    student = application.student
    public_docs = StudentDocument.objects.filter(
        user=student,
        is_public=True
    ).order_by("-created_at")
    if request.method == 'POST':
        new_status = request.POST.get('status')
        rating = request.POST.get('rating')
        note = request.POST.get('company_note')
    

        valid_status = dict(Application.STATUS_CHOICES).keys()
        if new_status not in valid_status:
            messages.error(request, "Statut invalide.")
            return redirect('company_offer_applications', slug=application.offer.slug)

        old_status = application.status

        # Statut
        application.status = new_status
        application.status_changed_at = timezone.now()

        # Rating (optionnel)
        if rating:
            try:
                r = int(rating)
                if 1 <= r <= 5:
                    application.rating = r
            except ValueError:
                pass

        # Note entreprise
        application.company_note = note
        # 🎯 Si la candidature vient d'être ACCEPTÉE → créer une conversation
        if old_status != "accepted" and new_status == "accepted":
            conv, created = Conversation.objects.get_or_create(
                application=application,
                defaults={
                    "student": application.student,
                    "company": application.offer.company,
                }
            )
            if created:
                # Message de bienvenue système (optionnel)
                Message.objects.create(
                    conversation=conv,
                    sender=application.offer.company,
                    text=(
                        "Bonjour, votre candidature a été acceptée 🎉 "
                        "Nous pouvons échanger ici pour organiser la suite."
                    ),
                )
        # 🔔 Notification + email pour l'étudiant
        if old_status != new_status:
            send_application_status_notification(application, old_status, new_status)
        messages.success(request, "Candidature mise à jour.")
        return redirect('company_offer_applications', slug=application.offer.slug)
    return render(request, 'stages/company_application_update.html', {
        'application': application,
        'public_docs': public_docs,
    })
def send_application_status_notification(application, old_status, new_status):
    """
    Crée une Notification + envoie un email à l'étudiant
    quand le statut de sa candidature change.
    - old_status : ancien statut (str)
    - new_status : nouveau statut (str)
    """
    student = application.student
    offer = application.offer
    if not student:
        return
    has_email = bool(student.email)

    # Libellés lisibles pour l'utilisateur
    status_labels = {
        'submitted': "envoyée",
        'viewed': "consultée",
        'shortlisted': "pré-sélectionnée",
        'rejected': "refusée",
        'accepted': "acceptée",
    }
    base_url = getattr(settings,"SITE_BASE_URL","http://localhost:8000")
    status_label = status_labels.get(new_status, new_status)
    # On choisit quels statuts déclenchent une notif
    statuses_to_notify = ['viewed', 'shortlisted', 'accepted', 'rejected']
    if new_status not in statuses_to_notify:
        return
    # Message de base
    base_message = (
        f"Le statut de votre candidature pour « {offer.title} » "
        f"est maintenant : {status_label}."
    )
    # Texte complémentaire en fonction du statut
    if new_status == 'viewed':
        extra = "L'entreprise a consulté votre profil."
    elif new_status == 'shortlisted':
        extra = "Vous avez été pré-sélectionné(e) pour la suite du processus."
    elif new_status == 'accepted':
        extra = (
            "Félicitations ! Votre candidature a été acceptée. "
            "L'entreprise pourra vous contacter pour organiser la suite."
        )
    elif new_status == 'rejected':
        extra = (
            "Votre candidature n'a pas été retenue pour cette offre. "
            "Ne vous découragez pas et continuez à postuler à d'autres opportunités."
        )
    else:
        extra = ""

    full_message = base_message
    if extra:
        full_message += "\n\n" + extra
     
    Notification.objects.create(
        user=student,
        notif_type='status_update',
        message=full_message,
        offer=application.offer,
        application=application,
    )

    if student.email:
        subject = f"Mise à jour candidature : {new_status}"
        html_message = render_to_string('emails/application_status_update.html', {
            'student': student, 'offer': application.offer, 'base_url': base_url
        })

        # Envoi ASYNCHRONE
        EmailThread(
            subject, 
            full_message, 
            getattr(settings, 'DEFAULT_FROM_EMAIL', None), 
            [student.email],
            html_message=html_message
        ).start()
from django.utils import timezone
from accounts.decorators import company_required
from django.shortcuts import get_object_or_404, render
from .models import StageOffer, Application, Notification
# send_application_status_notification doit être importé où il est défini
@company_required
def company_offer_applications_view(request, slug):
    """
    Liste les candidatures pour une offre donnée (vue entreprise).
    Et marque comme 'viewed' les candidatures encore 'submitted'
    dès que l'entreprise les voit dans la liste.
    """
    offer = get_object_or_404(StageOffer, slug=slug, company=request.user)

    applications = (
        Application.objects
        .select_related('student', 'student__profile', 'cv')  # 👈 profil chargé ici
        .filter(offer=offer)
        .order_by('-created_at')
    )

    # 🔥 Auto : marquer comme 'viewed' les candidatures encore 'submitted'
    submitted_apps = applications.filter(status='submitted')

    for app in submitted_apps:
        old_status = app.status
        app.status = 'viewed'
        app.status_changed_at = timezone.now()
        app.save(update_fields=['status', 'status_changed_at'])
        # envoie notif + email à l'étudiant
        send_application_status_notification(app, old_status, 'viewed')

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        applications = applications.filter(status=status_filter)

    context = {
        "offer": offer,
        "applications": applications,
        "status_filter": status_filter,
        "status_choices": Application.STATUS_CHOICES,
    }
    return render(request, "stages/company_offer_applications.html", context)
@login_required
def stages_test_view(request):
    return render(request,"stages/test_stages.html")


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import student_required

from .models import StageOffer
   # si tu l'as mis dans utils, sinon adapte


@student_required
@profile_completion_required
def motivation_letter_template_view(request, slug):
    """
    Génère et affiche une lettre de motivation complète
    pour une offre donnée, avant candidature.
    """
    offer = get_object_or_404(
        StageOffer,
        slug=slug,
        is_active=True,
        status='published'
    )

    # Génération automatique de la lettre
    letter_text = build_motivation_letter(request.user, offer)

    return render(request, "stages/motivation_letter_template.html", {
        "offer": offer,
        "text": letter_text,
    })
    
    
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# ... tes autres imports en haut du fichier ...


@student_required
@profile_completion_required
def motivation_letter_pdf_view(request, slug):
    """
    Génère un PDF téléchargeable de la lettre de motivation
    pour une offre donnée.
    """
    offer = get_object_or_404(
        StageOffer,
        slug=slug,
        is_active=True,
        status='published'
    )

    # On s'assure d'avoir les données les plus récentes
    user = request.user
    user.refresh_from_db()
    
    try:
        profile = Profile.objects.get(user=user)
        profile.refresh_from_db()
    except Profile.DoesNotExist:
        pass

    # 1) Récupérer le texte de la lettre
    text = build_motivation_letter(user, offer)

    # 2) Préparer un buffer mémoire
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    x_margin = 40
    y = height - 50  # position de départ en haut

    # 3) Écrire ligne par ligne (avec wrap basique)
    for line in text.split("\n"):
        if not line.strip():
            y -= 16  # saut de ligne
            continue

        # découpe la ligne si elle est trop longue
        max_chars = 100
        while len(line) > max_chars:
            part = line[:max_chars]
            p.drawString(x_margin, y, part)
            line = line[max_chars:]
            y -= 16
            if y < 50:
                p.showPage()
                y = height - 50

        p.drawString(x_margin, y, line)
        y -= 16
        if y < 50:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()

    # 4) Renvoyer la réponse HTTP avec le PDF
    buffer.seek(0)
    filename = f"lettre_motivation_{offer.slug}.pdf"

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@company_required
def company_offer_change_status_view(request, slug, new_status):
    """
    Change le statut d'une offre :
      - draft
      - published
      - archived
    Met à jour is_active en fonction du statut.
    """
    offer = get_object_or_404(StageOffer, slug=slug, company=request.user)

    allowed_statuses = ['draft', 'published', 'archived']
    if new_status not in allowed_statuses:
        messages.error(request, "Statut invalide.")
        return redirect('company_offers')

    if request.method == 'POST':
        offer.status = new_status
        offer.is_active = (new_status == 'published')
        offer.save()
        messages.success(request, f"Offre mise à jour : {offer.get_status_display()}.")
        return redirect('company_offers')

    # si on arrive en GET par erreur, on redirige
    return redirect('company_offers')


from django.utils import timezone
from accounts.decorators import student_required
from accounts.models import Profile
from stages.models import StageOffer, Application, StudentDocument
from orientation.models import OrientationResult


@student_required
def student_opportunities_dashboard_view(request):
    """
    Dashboard étudiant 'Mes opportunités' avec un bloc
    'À faire aujourd'hui'.
    """
    user = request.user
    profile = getattr(user, "profile", None)

    # 1) A-t-il un CV par défaut ?
    has_default_cv = StudentDocument.objects.filter(
        user=user,
        doc_type="cv",
        is_default_cv=True
    ).exists()

    # 2) Depuis combien de jours n'a-t-il pas postulé ?
    last_application = (
        Application.objects
        .filter(student=user)
        .order_by("-created_at")
        .first()
    )

    days_since_last_application = None
    if last_application:
        delta = timezone.now() - last_application.created_at
        days_since_last_application = delta.days

    # 3) Offre qui matche et se termine demain
    today = timezone.now().date()
    tomorrow = today + timezone.timedelta(days=1)

    last_orientation = (
        OrientationResult.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    matching_offers_ending_tomorrow = StageOffer.objects.none()

    if last_orientation:
        suggested_tracks = last_orientation.suggested_tracks.all()
        if suggested_tracks.exists():
            matching_offers_ending_tomorrow = (
                StageOffer.objects
                .filter(
                    is_active=True,
                    status='published',
                    application_deadline=tomorrow,
                    related_tracks__in=suggested_tracks,
                )
                .distinct()
                .order_by("application_deadline", "-created_at")
            )

    # Construire la liste des tâches à faire aujourd'hui
    todo_items = []

    if not has_default_cv:
        todo_items.append({
            "code": "no_cv",
            "text": "Tu n’as pas encore de CV généré. Génère ton CV pour postuler plus facilement.",
        })

    if days_since_last_application is None:
        todo_items.append({
            "code": "never_applied",
            "text": "Tu n’as encore jamais postulé à une offre. Lance-toi sur ta première opportunité !",
        })
    elif days_since_last_application >= 7:
        todo_items.append({
            "code": "no_recent_applications",
            "text": f"Tu n’as pas postulé à une offre depuis {days_since_last_application} jours.",
        })

    if matching_offers_ending_tomorrow.exists():
        offer = matching_offers_ending_tomorrow.first()
        todo_items.append({
            "code": "offer_ending_tomorrow",
            "text": (
                f"Une offre qui correspond à ton profil se termine demain : "
                f"« {offer.title} »."
            ),
            "offer": offer,
        })
    feedbacks = CompanyFeedbacke.objects.filter(student=request.user).order_by("-created_at")



    context = {
        "profile": profile,
        "todo_items": todo_items,
        "matching_offers_ending_tomorrow": matching_offers_ending_tomorrow[:3],
        "last_application": last_application,
        "has_default_cv": has_default_cv,
        "feedbacks": feedbacks,
    }
    return render(request, "stages/student_dashboard.html", context)


from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone

from accounts.decorators import student_required
from .models import Application, StageReview
from .forms import StageReviewForm


from django.shortcuts import render
from django.contrib import messages
from accounts.decorators import company_required
from .models import StageOffer, StageReview, Application
from .utils_stats import get_company_rating_stats
@login_required
@role_required(['student'])
def submit_company_review(request, slug):
    # On récupère l'offre directement via le slug
    offer = get_object_or_404(StageOffer, slug=slug)
    
    # LOGIQUE ANTI-SPAM : Un seul avis par étudiant et par offre
    # On utilise ton modèle StageReview qui a unique_together = ("offer", "student")
    if StageReview.objects.filter(offer=offer, student=request.user).exists():
        messages.warning(request, "Vous avez déjà laissé un avis pour cette opportunité.")
        return redirect('offer_detail', slug=slug)

    if request.method == 'POST':
        form = StageReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = request.user
            review.offer = offer
            review.company = offer.company
            
            # OPTIONNEL : On essaie quand même de lier une candidature si elle existe
            # Cela permet de garder une trace si l'étudiant avait quand même postulé
            review.application = Application.objects.filter(offer=offer, student=request.user).first()
            
            review.save()
            
            messages.success(request, "Merci ! Votre avis sur l'entreprise a été publié.")
            # Redirection vers le détail de l'offre (ou le profil entreprise selon ta préférence)
            return redirect('offer_detail', slug=slug)
    else:
        form = StageReviewForm()
    
    return render(request, 'stages/submit_company_review.html', {
        'form': form,
        'offer': offer,
        # On passe l'entreprise pour l'affichage du nom dans le titre du template
        'company': offer.company 
    })
@company_required
def company_dashboard_view(request):
    """
    Dashboard entreprise :
      - note moyenne donnée par les étudiants
      - nombre d'avis
      - liste des derniers avis
      - quelques stats simples sur les offres / candidatures
    """
    company = request.user

    # ⭐ Stats de rating global
    rating_stats = get_company_rating_stats(company)

    # 📝 Derniers avis publics reçus
    latest_reviews = (
        StageReview.objects
        .filter(company=company, is_public=True)
        .select_related("student", "offer")
        .order_by("-created_at")[:10]
    )

    # 📊 Stats simples sur les offres / candidatures
    offers_count = StageOffer.objects.filter(company=company).count()
    active_offers_count = StageOffer.objects.filter(company=company, is_active=True, status="published").count()

    total_applications = (
        Application.objects
        .filter(offer__company=company)
        .count()
    )
    accepted_applications = (
        Application.objects
        .filter(offer__company=company, status="accepted")
        .count()
    )

    context = {
        "rating_stats": rating_stats,
        "latest_reviews": latest_reviews,
        "offers_count": offers_count,
        "active_offers_count": active_offers_count,
        "total_applications": total_applications,
        "accepted_applications": accepted_applications,
    }
    return render(request, "stages/company_dashboard.html", context)

# ---- Notifications messages non lus ----
UNREAD_EMAIL_THRESHOLD = 5          # nb de messages non lus avant mail
UNREAD_EMAIL_COOLDOWN_HOURS = 6   # délai mini entre 2 mails pour la même conv / user

from django.conf import settings
from django.core.mail import send_mail

def send_unread_messages_email(receiver, conversation, unread_count):
    """
    Envoie un email à `receiver` pour l'informer qu'il a `unread_count`
    messages non lus dans `conversation`.

    Compatible :
      - conversations stages (avec application / offer)
      - conversations services (liées à une commande ServiceOrder)
    """
    if not receiver.email:
        return

    # Qui est l’autre ?
    if hasattr(conversation, "student") and hasattr(conversation, "company"):
        # modèle actuel pour stages/services
        other = conversation.student if receiver == conversation.company else conversation.company
    else:
        # fallback très large
        other = None

    # 🔹 On essaie d'abord de récupérer un "titre de contexte" (offre / service)
    context_title = None

    # 1) Cas offre de stage / emploi
    application = getattr(conversation, "application", None)
    if application is not None:
        offer = getattr(application, "offer", None)
        if offer is not None and getattr(offer, "title", None):
            context_title = offer.title

    # 2) Cas commande de service (conversation liée à ServiceOrder)
    if context_title is None:
        # selon comment tu as nommé la FK dans ServiceOrder
        # ex : conversation = models.ForeignKey(Conversation, related_name="service_orders", ...)
        service_order = None

        # d'abord via related_name normal
        if hasattr(conversation, "service_orders"):
            service_order = conversation.service_orders.first()
        # ou si tu avais une OneToOne ou un nom différent :
        if service_order is None:
            service_order = getattr(conversation, "service_order", None)

        if service_order is not None:
            # tu peux adapter selon les champs disponibles
            if getattr(service_order, "service_title_snapshot", None):
                context_title = service_order.service_title_snapshot
            elif getattr(service_order, "service", None) and getattr(service_order.service, "title", None):
                context_title = service_order.service.title

    # 3) Fallback générique
    if context_title is None:
        context_title = "votre échange"

    site_name = getattr(settings, "SITE_NAME", "CampusHub")
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

    # lien direct vers la conversation (adapte le nom d'URL si besoin)
    try:
        from django.urls import reverse
        conv_url = base_url + reverse("messaging_conversation", args=[conversation.id])
    except Exception:
        conv_url = base_url

    subject = f"[{site_name}] {unread_count} nouveau(x) message(s) non lu(s)"

    other_name = other.username if other else "un autre utilisateur"

    message = (
        f"Bonjour {receiver.username},\n\n"
        f"Vous avez {unread_count} nouveau(x) message(s) non lu(s) de "
        f"{other_name} à propos de « {context_title} ».\n\n"
        f"Pour répondre rapidement, connectez-vous et ouvrez la conversation :\n"
        f"{conv_url}\n\n"
        f"Merci d'utiliser {site_name}.\n"
    )
    # Envoi ASYNCHRONE
    EmailThread(
        subject, 
        message, 
        getattr(settings, "DEFAULT_FROM_EMAIL", None), 
        [receiver.email]
    ).start()


from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Conversation

from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Conversation  # adapter si besoin


@login_required
def messaging_inbox_view(request):
    """
    Liste les conversations de l'utilisateur :
      - par défaut : non archivées pour lui
      - si ?archived=1 : conversations archivées pour lui
      - gère aussi les conversations liées à des commandes de services
    """
    user = request.user
    show_archived = request.GET.get("archived") == "1"
    base_qs = (
        Conversation.objects
        .filter(is_active=True)
        .filter(Q(student=user) | Q(company=user))
        .select_related(
            "student",
            "company",
            "application__offer",
            "service_order",
            "participation",
            "participation__challenge",
        )
        .prefetch_related("messages")
        # 🔥 OPTIMISATION : On compte les non-lus directement en SQL
        .annotate(
            unread_count_computed=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user)
            )
        )
    )

    # 2. Filtrage Archive
    if show_archived:
        conversations = base_qs.filter(
            Q(student=user, is_archived_student=True) |
            Q(company=user, is_archived_company=True)
        )
    else:
        conversations = base_qs.filter(
            Q(student=user, is_archived_student=False) |
            Q(company=user, is_archived_company=False)
        )

    conversations = conversations.order_by("-updated_at")

    # 3. Traitement des résultats (plus rapide car données déjà là)
    # Note : La logique d'envoi d'email de rappel ("cooldown") devrait être gérée 
    # lors de la réception d'un message (dans messaging_conversation_view POST), 
    # pas lors de l'affichage de l'inbox, pour éviter de ralentir cette page.
    
    for conv in conversations:
        # On utilise la valeur calculée par SQL .annotate()
        conv.unread_count_for_user = conv.unread_count_computed
        conv.has_unread_for_user = conv.unread_count_computed > 0

    return render(request, "stages/messaging_inbox.html", {
        "conversations": conversations,
        "show_archived": show_archived,
    })

    
@login_required
def messaging_archive_conversation_view(request, pk):
    """
    Archive une conversation pour l'utilisateur connecté.
    Ne supprime rien, ne l'archive pas pour l'autre partie.
    """
    conv = get_object_or_404(
        Conversation,
        pk=pk,
        is_active=True,
    )

    if request.user != conv.student and request.user != conv.company:
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect("messaging_inbox")

    if request.method == "POST":
        conv.archive_for_user(request.user)
        messages.success(request, "Conversation archivée.")
        return redirect("messaging_inbox")

    # si GET direct, on redirige
    return redirect("messaging_inbox")


@login_required
def messaging_unarchive_conversation_view(request, pk):
    """
    Désarchive une conversation pour l'utilisateur connecté.
    """
    conv = get_object_or_404(
        Conversation,
        pk=pk,
        is_active=True,
    )

    if request.user != conv.student and request.user != conv.company:
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect("messaging_inbox")

    if request.method == "POST":
        conv.unarchive_for_user(request.user)
        messages.success(request, "Conversation restaurée.")
        return redirect("messaging_inbox",)

    return redirect("messaging_inbox")
# Seuil à partir duquel on envo
@login_required
def messaging_conversation_view(request, pk):
    """
    Affiche une conversation + permet d'envoyer des messages,
    avec :
      - vérification d'accès
      - limite par trust_score
      - mute / strikes si contenu interdit
      - messages système
      - marquage des messages reçus comme lus
      - email si trop de messages non lus
      - avertissement si infos sensibles (tel, email, réseaux, whatsapp...)
    """
    user = request.user
    profile = getattr(user, "profile", None)

    # 🔐 limite par trust_score pour envoyer des messages (mais on laisse voir la conv)
    MIN_TRUST_FOR_MESSAGING = 20

    # Récupérer la conversation
    conv = get_object_or_404(
        Conversation.objects.select_related(
            "application",
            "student",
            "company",
            "application__offer",
        ),
        pk=pk,
        is_active=True,
    ) 
    #Jitsi : session d'appel pour cette conversation
    call_session = getattr(conv, "call_session", None)


    # Qui est “l’autre” côté ?
    other = conv.student if request.user == conv.company else conv.company
    other_profile = getattr(other, "profile", None)

# Mettre à jour "ma" présence (au GET et au POST si tu veux)
    my_profile = getattr(request.user, "profile", None)
    if my_profile:
        my_profile.last_chat_seen = timezone.now()
        my_profile.save(update_fields=["last_chat_seen"])
    # Autorisation d'accès
    if user != conv.student and user != conv.company:
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect("messaging_inbox")
    

    window_data = None
    # ---------------------------------------------------
    # POST : tentative d'envoi d'un message
    # ---------------------------------------------------
    if request.method == "POST":
        # 1) Trust score trop bas → on bloque l'envoi mais on laisse voir
        if profile and profile.trust_score is not None and profile.trust_score < MIN_TRUST_FOR_MESSAGING:
            messages.error(
                request,
                "Ton compte a été temporairement limité. "
                "Ton score de confiance est trop bas pour envoyer de nouveaux messages. "
                "Contacte le support si tu penses que c’est une erreur."
            )
            return redirect("messaging_conversation", pk=conv.pk)

        # 2) Mute dans cette conversation ?
        if conv.is_user_muted(user):
            messages.error(
                request,
                "Tu as été temporairement restreint d'envoyer des messages dans cette conversation "
                "à cause de plusieurs violations des règles."
            )
            return redirect("messaging_conversation", pk=conv.pk)
        
        
        attachment = None
        attachment_mime = ""
        attachment_size = 0


        # 3) Récupérer le texte
        text = (request.POST.get("text") or "").strip()
        uploaded_file = request.FILES.get("attachment")
        attachment = uploaded_file
        attachment_size = getattr(uploaded_file, "size", 0) or 0
        attachment_mime = detect_mime(uploaded_file)
        
        if not text and not uploaded_file:
            messages.error(request,"Le message est vide.")
        now = timezone.now()
        
        cache_key = f"chat_rate_{user.id}"
        
        window_data = cache.get(cache_key)
        max_per_minute = getattr(settings, "CHAT_MAX_MESSAGES_PER_MINUTE", 30)
            
        # 5) Contenu OK → créer le message normal 
        # 🔒 Rate limit simple par utilisateur : X messages / minute
        
        if not window_data:
            # première fois
            window_data = {"start": now.timestamp(), "count": 0}

        elapsed = now.timestamp() - window_data["start"]

        if elapsed > 60:
            # nouvelle fenêtre de 60s
            window_data = {"start": now.timestamp(), "count": 0}

        window_data["count"] += 1
        cache.set(cache_key, window_data, timeout=120)  # conserve un peu

        if window_data["count"] > max_per_minute:
            messages.error(
                request,
                "Tu envoies beaucoup de messages trop vite. "
                "Merci de ralentir un peu pour éviter le spam."
            )
            return redirect("messaging_conversation", pk=conv.pk)



        # si rien du tout → on refuse
        if not text and  uploaded_file:
            if is_too_big(uploaded_file):
                messages.error(
                    request,
                    "Le fichier est trop volumineux (max 4 Mo)."
                )
                return redirect("messaging_conversation", pk=conv.pk)
            msg = Message.objects.create(
                conversation=conv,
                sender=user,
                text="",
                msg_type="normal",
                attachment=attachment,
                attachment_size=attachment_size,
                attachment_mime=attachment_mime,                 
                
            )
            
            conv.updated_at = timezone.now()
            conv.save(update_fields=["updated_at"])
            return redirect("messaging_conversation", pk=conv.pk)
       

            
            
            
            
        

        # --- Validation / scan du fichier s'il existe ---

        if uploaded_file:
            # taille max
            
            # extension autorisée
            if not is_extension_allowed(uploaded_file):
                messages.error(
                    request,
                    "Ce type de fichier n'est pas autorisé. "
                    "Formats acceptés : images, PDF, TXT, DOC/DOCX."
                )
                return redirect("messaging_conversation", pk=conv.pk)
            

            # scan sensible dans le contenu texte (si possible)
            if scan_attachment_for_sensitive_info(uploaded_file):
                messages.warning(
                    request,
                    "⚠️ Le fichier envoyé semble contenir des informations personnelles "
                    "(numéro, email, réseaux sociaux…). "
                    "Évite de partager ces infos : cela peut mener à du harcèlement ou des arnaques."
                )

            
        # 3bis) Vérification info sensible (tel / email / whatsapp / réseaux sociaux...)
        if text and contains_sensitive_info(text):
            messages.warning(
                request,
                "⚠️ Ton message semble contenir des infos personnelles "
                "(numéro, email, WhatsApp, réseaux sociaux). "
                "Évite de partager ces infos : cela peut mener à du harcèlement ou des arnaques."
            )
            # on laisse quand même passer côté backend, tu gères le modal côté front

        # 4) Vérifier le contenu (insultes, spam, etc.)
        ok, error_code, error_msg = validate_message_content(text)

        if not ok:
            # ➕ Strike pour l'utilisateur
            muted_now = conv.add_strike_for_user(user)

            # Message système dans la conversation (affiché dans le chat)
            system_text = error_msg or "Message refusé pour contenu interdit."
            if muted_now:
                system_text += (
                    "\n\nTu as atteint la limite de tentatives. "
                    "Tu es temporairement mute dans cette conversation."
                )

            Message.objects.create(
                conversation=conv,
                sender=user,   # tu peux mettre sender=None si tu veux un pur message système
                text=system_text,
                msg_type="system",
            )

            messages.error(request, error_msg or "Ce message n'est pas autorisé.")
            return redirect("messaging_conversation", pk=conv.pk)

        # 5) Contenu OK → créer le message normal
        if text:
            msg = Message.objects.create(
                conversation=conv,
                sender=user,
                text=text,
                msg_type="normal",
                attachment=attachment,
                attachment_size=attachment_size,
                attachment_mime=attachment_mime,                 
                
            )
            conv.updated_at = timezone.now()
            conv.save(update_fields=["updated_at"])

            # 🔔 Vérifier si on atteint le seuil de messages non lus pour le destinataire
            receiver = conv.student if user == conv.company else conv.company

            unread_count = (
                conv.messages
                .filter(is_read=False)
                .exclude(sender=receiver)
                .count()
            )

            # On envoie l'email exactement quand on atteint le seuil (ex : 5ᵉ msg non lu)
            if unread_count == UNREAD_EMAIL_THRESHOLD:
                now = timezone.now()

                if receiver == conv.student:
                    last_reminder = conv.student_last_reminder_at
                else:
                    last_reminder = conv.company_last_reminder_at

                cooldown_ok = (
                    not last_reminder or
                    (now - last_reminder).total_seconds() >= UNREAD_EMAIL_COOLDOWN_HOURS * 3600
                )

                if cooldown_ok:
                    # 👉 nouvelle fonction robuste, compatible stages + services
                    send_unread_messages_email(receiver, conv, unread_count)

                    if receiver == conv.student:
                        conv.student_last_reminder_at = now
                    else:
                        conv.company_last_reminder_at = now

                    conv.save(update_fields=["student_last_reminder_at", "company_last_reminder_at"])

        return redirect("messaging_conversation", pk=conv.pk)

    # ---------------------------------------------------
    # GET (ou après redirection) : afficher la conversation
    # ---------------------------------------------------

    # Marquer comme lus les messages reçus
    (
        conv.messages
        .filter(is_read=False)
        .exclude(sender=user)
        .update(is_read=True)
    )

    messages_list = (
        conv.messages
        .select_related("sender")
        .order_by("created_at")
    )

    # Optionnel : dernier message système
    last_system_message = (
        conv.messages
        .filter(msg_type="system")
        .order_by("-created_at")
        .first()
    )

    # 🔹 Réponses rapides seulement côté entreprise
    quick_replies = []
    if user == conv.company:
        quick_replies = QuickReply.objects.filter(
            is_active=True
        ).filter(
            Q(is_global=True, for_role__in=["company", None]) |
            Q(owner=user, for_role__in=["company", None])
        ).order_by("label")
        
    # ... tout ton code pour la conversation, messages, quick_replies, etc. ...

    # ---------- APPEL EXTERNE (Daily / Whereby / autre) ----------
    base_url = getattr(settings, "CALL_PROVIDER_BASE_URL", "").rstrip("/")
    if base_url:
        # URL unique par conversation
        call_url = f"{base_url}{conv.id}"
    else:
        call_url = ""

    # Limite de confiance pour lancer un appel
    profile = getattr(user, "profile", None)
    trust = getattr(profile, "trust_score", None) or 0
    CALL_MIN_TRUST = 20
    call_allowed = bool(call_url) and (trust >= CALL_MIN_TRUST)


    return render(request, "stages/messaging_conversation.html", {
        "conversation": conv,
        "other": other,
        "other_profile": other_profile,
        "messages_list": messages_list,
        "call_url": call_url,
        "system_message": last_system_message,
        "my_profile": my_profile,
        "quick_replies": quick_replies,
        "call_allowed": call_allowed,

    })
from .models import ConversationBlock, ConversationReport

@login_required
def conversation_block_view(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)

    if request.user != conv.student and request.user != conv.company:
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect("messaging_inbox")

    if request.method == "POST":
        # Qui est bloqué ?
        if request.user == conv.student:
            blocked = conv.company
        else:
            blocked = conv.student

        ConversationBlock.objects.get_or_create(
            conversation=conv,
            blocker=request.user,
            blocked=blocked,
        )
        messages.success(request, "L'utilisateur a été bloqué. Il ne pourra plus vous écrire.")
    return redirect("messaging_conversation", pk=pk)


@login_required
def conversation_report_view(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)

    if request.user != conv.student and request.user != conv.company:
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect("messaging_inbox")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Veuillez expliquer le problème.")
            return redirect("messaging_conversation", pk=pk)

        if request.user == conv.student:
            reported = conv.company
        else:
            reported = conv.student

        ConversationReport.objects.create(
            conversation=conv,
            reporter=request.user,
            reported=reported,
            reason=reason,
        )
        messages.success(request, "Votre signalement a été transmis à l'équipe CampusHub.")
    return redirect("messaging_conversation", pk=pk)



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages

from .models import Message

@login_required
def message_delete_view(request, pk):
    """
    Permet à l'expéditeur de marquer son message comme supprimé.
    """
    msg = get_object_or_404(
        Message.objects.select_related("conversation", "sender"),
        pk=pk
    )

    if request.user != msg.sender:
        messages.error(request, "Tu ne peux supprimer que tes propres messages.")
        return redirect("messaging_conversation", pk=msg.conversation_id)

    if request.method == "POST":
        msg.is_deleted = True
        msg.text = ""  # on efface le contenu
        msg.edited_at = timezone.now()
        msg.save(update_fields=["is_deleted", "text", "edited_at"])
        messages.success(request, "Message supprimé.")
    return redirect("messaging_conversation", pk=msg.conversation_id)


@login_required
def message_edit_view(request, pk):
    """
    Permet à l'expéditeur de modifier le texte de son message.
    (on ne permet pas l'édition des messages système ou supprimés)
    """
    msg = get_object_or_404(
        Message.objects.select_related("conversation", "sender"),
        pk=pk
    )

    if request.user != msg.sender:
        messages.error(request, "Tu ne peux modifier que tes propres messages.")
        return redirect("messaging_conversation", pk=msg.conversation_id)

    if msg.msg_type == "system" or msg.is_deleted:
        messages.error(request, "Ce message ne peut pas être modifié.")
        return redirect("messaging_conversation", pk=msg.conversation_id)

    if request.method == "POST":
        new_text = (request.POST.get("text") or "").strip()
        if not new_text:
            messages.error(request, "Le message ne peut pas être vide.")
            return redirect("messaging_conversation", pk=msg.conversation_id)

        msg.text = new_text
        msg.edited_at = timezone.now()
        msg.save(update_fields=["text", "edited_at"])
        messages.success(request, "Message modifié.")
        return redirect("messaging_conversation", pk=msg.conversation_id)

    # Si GET, on ne veut pas de page séparée → on redirige vers la conv
    return redirect("messaging_conversation", pk=msg.conversation_id)

# en haut de views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from accounts.decorators import student_required
from .models import StageOffer, SavedOffer
@plus_required
@student_required
def toggle_save_offer_view(request, slug):
    """
    Ajoute ou supprime une offre de la liste des favoris de l'étudiant.
    - Si déjà sauvegardée → on supprime
    - Sinon → on crée
    """
    offer = get_object_or_404(StageOffer, slug=slug, is_active=True, status="published")

    saved_obj, created = SavedOffer.objects.get_or_create(
        student=request.user,
        offer=offer,
    )

    if created:
        messages.success(request, "Offre ajoutée à vos favoris.")
        saved = True
    else:
        saved_obj.delete()
        messages.info(request, "Offre retirée de vos favoris.")
        saved = False

    # Si tu veux supporter l'AJAX (JSON)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": saved})

    # Sinon, simple redirect vers la page de l'offre
    return redirect("offer_detail", slug=slug)


@student_required
def saved_offers_list_view(request):
    """
    Liste des offres sauvegardées par l'étudiant.
    """
    saved_qs = (
        SavedOffer.objects
        .filter(student=request.user)
        .select_related("offer", "offer__company")
        .order_by("-created_at")
    )

    offers = [s.offer for s in saved_qs]

    return render(request, "stages/saved_offers.html", {
        "saved_offers": saved_qs,
        "offers": offers,
    })
@student_required
def job_alerts_list_api(request):
    """
    Retourne la liste des alertes de recherche de l'étudiant connecté, au format JSON.
    Utilisé par le modal "Mes alertes".
    """
    alerts = (
        JobSearchAlert.objects
        .filter(student=request.user, is_active=True)
        .order_by("-created_at")
    )

    data = []
    for alert in alerts:
        parts = []
        if alert.q:
            parts.append(f"Mot-clé : {alert.q}")
        if alert.city:
            parts.append(f"Ville : {alert.city}")
        if alert.contract_type:
            parts.append(f"Contrat : {alert.contract_type}")
        if alert.location_type:
            parts.append(f"Mode : {alert.location_type}")

        label = " / ".join(parts) if parts else "Recherche sans critère"

        data.append({
            "id": alert.id,
            "label": label,
            "created_at": alert.created_at.strftime("%d/%m/%Y"),
            "last_matched_at": alert.last_matched_at.strftime("%d/%m/%Y") if alert.last_matched_at else None,
        })

    return JsonResponse({"alerts": data})



@student_required
def delete_job_alert_api(request, alert_id):
    """
    Supprime (ou désactive) une alerte de recherche de l'étudiant, via AJAX.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    alert = JobSearchAlert.objects.filter(id=alert_id, student=request.user).first()
    if not alert:
        return JsonResponse({"error": "Alerte introuvable"}, status=404)

    # Tu peux soit supprimer, soit juste désactiver :
    # alert.is_active = False; alert.save(update_fields=["is_active"])
    alert.delete()

    return JsonResponse({"status": "success"})

from django.views.decorators.http import require_POST
from django.contrib import messages
from accounts.decorators import student_required  # comme ailleurs

@student_required
@require_POST
def disable_orientation_alerts_view(request):
    """
    Désactive toutes les futures alertes basées sur l'orientation pour cet étudiant.
    """
    profile = getattr(request.user, "profile", None)
    if profile and hasattr(profile, "receive_orientation_alerts"):
        profile.receive_orientation_alerts = False
        profile.save(update_fields=["receive_orientation_alerts"])
        messages.success(request, "Vous ne recevrez plus d'alertes basées sur votre orientation.")
    else:
        messages.error(request, "Impossible de mettre à jour vos préférences pour le moment.")

    # Redirige vers la page des notifications (adapte le nom)
    return redirect("notifications_list")


@student_required
@require_POST
def enable_orientation_alerts_view(request):
    """
    Réactive les futures alertes basées sur l'orientation pour cet étudiant.
    """
    profile = getattr(request.user, "profile", None)
    if profile and hasattr(profile, "receive_orientation_alerts"):
        profile.receive_orientation_alerts = True
        profile.save(update_fields=["receive_orientation_alerts"])
        messages.success(request, "Les alertes basées sur votre orientation sont réactivées.")
    else:
        messages.error(request, "Impossible de mettre à jour vos préférences pour le moment.")

    return redirect("notifications_list")

@company_required  # ou ton décorateur entreprise
def stage_offer_delete_view(request, pk):
    """
    Permet à une entreprise de supprimer ou fermer une offre de stage.

    - Si aucune candidature n'existe → suppression définitive.
    - Si des candidatures existent → on passe l'offre en 'archived'
      et on la désactive, puis on prévient les étudiants par email.
    """
    offer = get_object_or_404(
        StageOffer,
        pk=pk,
        company=request.user,  # sécurité : seule l’entreprise propriétaire
    )

    if request.method != "POST":
        messages.error(request, "La suppression d'une offre se fait uniquement en POST.")
        return redirect("company_offers")  # garde le slug ici

    # Vérifier s'il y a des candidatures
    has_applications = Application.objects.filter(offer=offer).exists()

    if not has_applications:
        title = offer.title
        offer.delete()
        messages.success(
            request,
            f"L'offre « {title} » a été supprimée définitivement."
        )
    else:
        offer.is_active = False
        offer.status = "archived"
        offer.save(update_fields=["is_active", "status"])

        student_ids = (
            Application.objects
            .filter(offer=offer)
            .values_list("student_id", flat=True)  # adapte si le champ est différent
            .distinct()
        )
        User = get_user_model()
        applicants = User.objects.filter(id__in=student_ids)

        notify_applicants_stage_offer_closed(offer, applicants)

        messages.info(
            request,
            "Cette offre avait déjà des candidatures. Elle a été fermée et "
            "les candidats concernés ont été prévenus par email."
        )

    return redirect("company_dashboard")  # ou ta vue tableau de bord entreprise

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone

@login_required
@require_POST
def chat_ping_view(request):
    """Met à jour last_chat_seen pour l’utilisateur courant."""
    prof = getattr(request.user, "profile", None)
    if not prof:
        return JsonResponse({"ok": False, "error": "no-profile"}, status=400)
    prof.last_chat_seen = timezone.now()
    prof.save(update_fields=["last_chat_seen"])
    return JsonResponse({"ok": True, "now": timezone.now().isoformat()})

@login_required
@require_GET
def chat_status_view(request, user_id):
    """Retourne le statut actuel d'un utilisateur (autre) pour rafraîchissement côté front."""
    User = get_user_model()
    try:
        other = User.objects.select_related("profile").get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not-found"}, status=404)

    p = getattr(other, "profile", None)
    if not p:
        return JsonResponse({"ok": True, "online": False, "name": other.username})

    data = {
        "ok": True,
        "online": p.is_chat_available_now,
        "name": getattr(p, "full_name", None) or other.username,
        "avatar": getattr(p, "avatar", None).url if getattr(p, "avatar", None) else "",
        "chat_start": p.chat_start_time.strftime("%H:%M") if p.chat_start_time else None,
        "chat_end": p.chat_end_time.strftime("%H:%M") if p.chat_end_time else None,
        "last_seen": p.last_chat_seen.isoformat() if p.last_chat_seen else None,
    }
    return JsonResponse(data)



# companies/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required


@login_required
def company_subscription_plans_view(request):
    """Affiche tous les plans disponibles pour les entreprises (système unifié)"""
    from accounts.models import SubscriptionPlan, Subscription
    from accounts.services import UsageManager

    if request.user.profile.role != "company":
        messages.error(request, "Accès réservé aux entreprises.")
        return redirect("home")

    # On récupère les plans pour entreprises
    plans = SubscriptionPlan.objects.filter(role_target='company', is_active=True).order_by('price')
    current_sub = getattr(request.user, 'user_subscription', None)
    
    # On prépare des stats d'usage spécifiques (ex: offres)
    usage_stats = {}
    if request.user.is_authenticated:
        usage_stats = {
            'offers': {
                'label': 'Offres de stage',
                'limit': UsageManager.get_limit_for_action(request.user, 'offer_publication'),
                # On pourrait ajouter le count ici si besoin
            }
        }

    return render(request, "stages/company_plans.html", {
        "plans": plans,
        "current_sub": current_sub,
        "usage_stats": usage_stats
    })


@login_required
def company_subscribe_view(request, plan_id):
    """Redirige vers le paiement ou active un plan gratuit (unifié)"""
    from accounts.models import SubscriptionPlan
    from django.urls import reverse

    if request.user.profile.role != "company":
        messages.error(request, "Accès refusé.")
        return redirect("home")

    plan = get_object_or_404(SubscriptionPlan, id=plan_id, role_target='company')

    # Si gratuit, on active (normalement via un signal ou une vue dédiée, mais ici on gère le redirect)
    if plan.price == 0:
        # Activer le plan gratuit si l'entreprise n'en a pas
        # Pour rester simple et cohérent avec accounts :
        return redirect(f"{reverse('subscribe', args=[plan.id])}")

    # Redirection vers le paiement
    return redirect(f"{reverse('payments:initiate_payment')}?plan_id={plan.id}&amount={plan.price}")



@login_required
@company_required
def company_feedback_view(request, application_id):
    """
    Permet à une entreprise de laisser un feedback sur un étudiant
    à partir d'une candidature existante.
    """
    application = get_object_or_404(Application, id=application_id)

    # Vérifie que l’utilisateur connecté est bien l’entreprise propriétaire de l’offre
    if request.user != application.offer.company:
        messages.error(request, "Vous n’êtes pas autorisé à laisser un avis sur cette candidature.")
        return redirect("offer_list")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if not content:
            messages.error(request, "Veuillez entrer un avis avant de soumettre.")
            return redirect("company_application_detail", pk=application.id)

        # Crée ou met à jour le feedback
        feedback, created = CompanyFeedbacke.objects.update_or_create(
            company=request.user,
            student=application.student,
            defaults={
                "content": content,
            }
        )

        messages.success(request, "✅ Votre avis a bien été enregistré.")
        return redirect("company_application_detail", pk=application.id)
    
import uuid

@login_required
def salle_interview_view(request, application_id):
    # Récupère la candidature
    application = get_object_or_404(Application, id=application_id)
    
    # Sécurité : Vérifie que c'est bien le candidat OU le recruteur
    if request.user != application.student.user and request.user != application.offer.recruiter:
        return HttpResponseForbidden("Vous n'avez pas accès à cet entretien.")

    # On crée un nom de salle unique basé sur l'ID de la candidature
    # Astuce : On peut hacher l'ID pour le rendre moins devinable
    unique_room_id = f"{application.id}-{application.offer.id}" 

    context = {
        'application': application,
        'unique_room_id': unique_room_id,
        # ... tes autres variables
    }
    return render(request, 'stages/interview_room.html', context)





from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import PlatformReview, Application # On importe Application pour vérifier l'activité

def analyze_sentiment_and_safety(text):
    """
    Analyse le texte pour détecter le sentiment et les mots interdits via regex.
    Retourne (score_sentiment, est_approuvé)
    """
    text_lower = text.lower()
    
    # Dictionnaire de mots pour le sentiment (Simplifié)
    positive_words = ['excellent', 'super', 'génial', 'top', 'parfait', 'merci', 'efficace', 'facile']
    negative_words = ['nul', 'mauvais', 'arnaque', 'lent', 'bug', 'déçu', 'horrible', 'pire']

    score = 0
    for word in positive_words:
        if word in text_lower: score += 1
    for word in negative_words:
        if word in text_lower: score -= 1

    # Vérification sécurité via le nouveau filtre regex
    is_safe, error_msg = validate_content_moderation(text)
    
    return score, is_safe

@login_required
def submit_platform_review(request):
    if request.method == "POST":
        user = request.user

        # --- PROTECTION SCRIPT : Rate Limiting manuel ---
        # On vérifie si l'utilisateur a déjà tenté d'écrire un avis il y a moins de 2 min
        # (évite les boucles de scripts de spam)
        last_review = PlatformReview.objects.filter(user=user).first()
        if last_review and (timezone.now() - last_review.updated_at).seconds < 120:
            messages.error(request, "Veuillez attendre 2 minutes entre chaque modification.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # --- PROTECTION ANTI-SPAM : Vérification d'activité réelle ---
        # Un étudiant doit avoir au moins 1 candidature pour donner son avis
        if hasattr(user, 'student_profile'):
            has_activity = Application.objects.filter(student=user).exists()
            if not has_activity:
                messages.error(request, "Vous devez avoir postulé à au moins une offre pour donner votre avis.")
                return redirect(request.META.get('HTTP_REFERER', '/'))

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not comment or not rating:
            messages.error(request, "Le commentaire et la note sont obligatoires.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # --- ANALYSE DE SENTIMENT ET SÉCURITÉ ---
        sentiment_score, is_safe = analyze_sentiment_and_safety(comment)
        
        # Si le score est très négatif ou contient des insultes, on n'approuve pas auto.
        auto_approve = is_safe and (sentiment_score > -2)

        # Détermination du rôle via le profil
        role = 'student' # default
        if hasattr(user, 'profile') and user.profile.role:
            role = user.profile.role

        review, created = PlatformReview.objects.update_or_create(
            user=user,
            defaults={
                'rating': int(rating),
                'comment': comment,
                'role_at_review': role,
                'is_approved': auto_approve 
            }
        )

        if not auto_approve:
            messages.warning(request, "Votre avis est en cours de modération par l'équipe.")
        else:
            messages.success(request, "Merci pour votre retour !")

    return redirect(request.META.get('HTTP_REFERER', '/'))


def reviews_list_view(request):
    # On récupère uniquement les avis approuvés
    reviews = PlatformReview.objects.filter(is_approved=True).order_by('-created_at')
    
    # On utilise la méthode de classe pour les stats globales
    stats = PlatformReview.get_global_stats()
    
    return render(request, 'stages/reviews.html', {
        'reviews': reviews,
        'avg_rating': stats['average'],
        'total_reviews': stats['total'],
    })
    
@login_required
def delete_review(request, review_id):
    review = get_object_or_404(PlatformReview, id=review_id, user=request.user)
    
    if request.method == "POST":
        review.delete()
        messages.success(request, "Votre avis a été supprimé avec succès.")
    
    return redirect('platform_reviews')
