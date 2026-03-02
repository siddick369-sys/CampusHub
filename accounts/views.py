from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from services.views import User
from stages.models import StageReview
from services.models import ServiceReview

from .forms import RegisterForm, ProfileForm
from .models import Profile
import random

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, ProfileForm, VerificationCodeForm
from .models import Profile
from .decorators import profile_completion_required, student_required,company_required,provider_required

# orientation_platform/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import threading
import random
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q

# Import des formulaires (assurez-vous que le chemin est bon)
from .forms import RegisterForm, ProfileForm, VerificationCodeForm, ServiceEmailSettingsForm, CompanyVerificationRequestForm
from .models import Profile, CompanyVerificationRequest
from .decorators import student_required, company_required, provider_required
from services.models import ProviderPenaltyLog, ServiceReview
from stages.models import StageReview

# -------------------------------------------------------------------
#  UTILITAIRES : EMAILS & SÉCURITÉ
# -------------------------------------------------------------------

class EmailThread(threading.Thread):
    """Envoi d'email en arrière-plan pour ne pas bloquer la page."""
    def __init__(self, subject, message, from_email, recipient_list):
        self.subject = subject
        self.message = message
        self.from_email = from_email
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                self.from_email,
                self.recipient_list,
                fail_silently=True
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")

def check_rate_limit(request, key_prefix, limit=5, timeout=60):
    """
    Vérifie si l'utilisateur dépasse la limite d'actions (Rate Limiting).
    Retourne True si bloqué, False sinon.
    """
    ip = request.META.get('REMOTE_ADDR')
    cache_key = f"rate_limit_{key_prefix}_{ip}"
    attempts = cache.get(cache_key, 0)

    if attempts >= limit:
        return True
    
    cache.set(cache_key, attempts + 1, timeout)
    return False

# -------------------------------------------------------------------
#  VUES AUTHENTIFICATION
# -------------------------------------------------------------------

@login_required
def home_view(request):
    """Page d'accueil."""
    user = request.user
    profile = getattr(user, "profile", None)
    return render(request, "home.html", {"user_obj": user, "profile": profile})

def register_view(request):
    """Inscription + Envoi code asynchrone."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Sécurité : Rate Limiting (max 5 essais / minute)
        if check_rate_limit(request, 'register', limit=5, timeout=60):
            messages.error(request, "Trop de tentatives. Veuillez patienter une minute.")
            return render(request, 'accounts/register.html', {'form': RegisterForm(request.POST)})

        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Mise à jour du profil
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.full_name = form.cleaned_data.get('full_name')
            profile.phone = form.cleaned_data.get('phone')
            profile.city = form.cleaned_data.get('city')
            profile.country = form.cleaned_data.get('country')
            
            profile.verification_code = code
            profile.email_verified = False
            
            # 🚀 Auto-activation du rôle prestataire si choisi à l'inscription
            if profile.role == 'provider':
                profile.is_service_provider = True
                
            profile.save()

            # Envoi Email Asynchrone
            sujet = "Code de vérification - CampusHub"
            message = (
                f"Bonjour {user.username},\n\n"
                f"Bienvenue sur CampusHub.\n"
                f"Votre code de vérification est : {code}\n\n"
                f"À bientôt !"
            )
            EmailThread(sujet, message, settings.EMAIL_HOST_USER, [user.email]).start()

            messages.success(request, "Compte créé. Vérifiez vos emails pour le code d'activation.")
            return redirect('verify_code')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

def verify_code_view(request):
    """Vérification du code."""
    if request.method == 'POST':
        # Sécurité : Rate Limiting (max 10 essais / minute pour éviter le brute force du code)
        if check_rate_limit(request, 'verify_code', limit=10, timeout=60):
            messages.error(request, "Trop de tentatives incorrectes. Veuillez patienter.")
            return redirect('verify_code')

        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            code = form.cleaned_data['code']

            try:
                profile = Profile.objects.select_related('user').get(user__email=email)
            except Profile.DoesNotExist:
                messages.error(request, "Aucun compte associé à cet email.")
                return redirect('verify_code')

            if profile.email_verified:
                messages.info(request, "Email déjà vérifié. Connectez-vous.")
                return redirect('login')

            if profile.verification_code == code:
                profile.email_verified = True
                profile.verification_code = "" # On vide le code
                profile.save()
                messages.success(request, "Email vérifié avec succès. Connectez-vous.")
                return redirect('login')
            else:
                messages.error(request, "Code incorrect.")
    else:
        form = VerificationCodeForm()

    return render(request, 'accounts/verify_code.html', {'form': form})

def resend_code_view(request):
    """Renvoi du code (limité pour éviter le spam)."""
    if request.method == 'POST':
        # Sécurité : Rate Limiting strict (1 email / minute)
        if check_rate_limit(request, 'resend_code', limit=1, timeout=60):
            messages.warning(request, "Veuillez attendre une minute avant de demander un nouveau code.")
            return redirect('verify_code')

        email = request.POST.get('email')
        try:
            profile = Profile.objects.select_related('user').get(user__email=email)
        except Profile.DoesNotExist:
            # On ne dit pas explicitement que l'user n'existe pas pour éviter le user enumeration
            messages.info(request, "Si ce compte existe, un code a été envoyé.")
            return redirect('verify_code')

        if profile.email_verified:
            messages.info(request, "Compte déjà vérifié.")
            return redirect('login')

        new_code = f"{random.randint(100000, 999999)}"
        profile.verification_code = new_code
        profile.save()

        sujet = "Nouveau code de vérification"
        message = f"Bonjour, votre nouveau code est : {new_code}"
        
        EmailThread(sujet, message, settings.DEFAULT_FROM_EMAIL, [profile.user.email]).start()

        messages.success(request, "Un nouveau code a été envoyé.")
        return redirect('verify_code')

    return render(request, 'accounts/resend_code.html')

def login_view(request):
    """Connexion sécurisée."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Sécurité : Rate Limiting (max 10 essais / minute)
        if check_rate_limit(request, 'login', limit=10, timeout=60):
            messages.error(request, "Trop de tentatives de connexion. Réessayez plus tard.")
            return render(request, 'accounts/login.html')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Veuillez remplir tous les champs.")
        else:
            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, "Identifiants incorrects.")
            else:
                if hasattr(user, 'profile') and not user.profile.email_verified:
                    messages.error(request, "Email non vérifié. Veuillez entrer votre code.")
                    return redirect('verify_code')

                login(request, user)
                # Redirection intelligente après login
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)

    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté.")
    return redirect('login')

# -------------------------------------------------------------------
#  GESTION PROFIL
# -------------------------------------------------------------------

@login_required
def delete_profil_view(request):
    """
    Suppression de compte sécurisée avec demande de mot de passe.
    """
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user
        
        # Vérification du mot de passe avant suppression
        if not user.check_password(password):
            messages.error(request, "Mot de passe incorrect. Suppression annulée.")
            return redirect('profile_edit') # Ou la page où se trouve le bouton supprimer

        logout(request) # Déconnecter avant de supprimer
        user.delete()
        messages.success(request, "Votre compte a été supprimé définitivement.")
        return redirect('home')
    
    # Si GET, on redirige (la suppression doit se faire via un form/modal en POST)
    return redirect('profile_edit')


@login_required
def profile_edit_view(request):
    """
    Permet de modifier son profil (et quelques infos utilisateur si tu veux plus tard)
    """
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('home')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'accounts/profile_edit.html', {'form': form,'profile':profile,})



# -------------------------------------------------------------------
#  PRÉFÉRENCES & PARAMÈTRES (Services)
# -------------------------------------------------------------------

@login_required
@profile_completion_required
def service_email_settings_view(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ServiceEmailSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Préférences mises à jour.")
            return redirect("service_email_settings")
    else:
        form = ServiceEmailSettingsForm(instance=profile)
    return render(request, "accounts/service_email_settings.html", {"form": form})

@login_required
@require_POST
def toggle_service_email_as_provider_view(request):
    profile = request.user.profile
    profile.service_email_as_provider = not profile.service_email_as_provider
    profile.save(update_fields=["service_email_as_provider"])
    msg = "Notifications prestataire activées." if profile.service_email_as_provider else "Notifications prestataire désactivées."
    messages.success(request, msg)
    return redirect(request.META.get("HTTP_REFERER", "service_email_settings"))

@login_required
@require_POST
def toggle_service_email_as_client_view(request):
    profile = request.user.profile
    profile.service_email_as_client = not profile.service_email_as_client
    profile.save(update_fields=["service_email_as_client"])
    msg = "Notifications client activées." if profile.service_email_as_client else "Notifications client désactivées."
    messages.success(request, msg)
    return redirect(request.META.get("HTTP_REFERER", "service_email_settings"))

# -------------------------------------------------------------------
#  ENTREPRISE & PRESTATAIRE
# -------------------------------------------------------------------

@company_required
def company_verification_request_view(request):
    profile = request.user.profile
    existing_request = CompanyVerificationRequest.objects.filter(company=request.user).order_by("-created_at").first()

    if request.method == "POST":
        form = CompanyVerificationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.company = request.user
            req.status = "pending"
            req.save()
            messages.success(request, "Demande envoyée. Examen en cours.")
            return redirect("company_dashboard")
    else:
        form = CompanyVerificationRequestForm()

    return render(request, "accounts/company_verification_request.html", {
        "form": form, "profile": profile, "existing_request": existing_request
    })

@login_required
def become_provider_view(request):
    return render(request, "accounts/become_provider.html")

# -------------------------------------------------------------------
#  TRUST SCORE & EXPORTS
# -------------------------------------------------------------------
# Note: Assurez-vous d'avoir les imports corrects pour HttpResponse, canvas, etc.
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from datetime import timedelta

@provider_required
@profile_completion_required
def trust_score_dashboard_view(request):
    """
    Mini dashboard montrant :
      - score de confiance actuel + niveau
      - historique filtrable (30j / 90j / 1 an / tout)
      - stats simples
    """
    user = request.user
    profile = getattr(user, "profile", None)

    if not profile:
        messages.error(request, "Profil introuvable.")
        return redirect("home")

    score = profile.trust_score or 0

    # 💠 Déterminer un niveau lisible
    if score >= 90:
        level = "Platine"
        level_desc = "Tu fais partie des prestataires ultra fiables. Garde ce niveau !"
        level_color = "success"
    elif score >= 75:
        level = "Or"
        level_desc = "Très bon niveau de confiance. Tu es bien vu par les clients."
        level_color = "primary"
    elif score >= 50:
        level = "Argent"
        level_desc = "Score correct, mais tu peux encore améliorer ta fiabilité."
        level_color = "info"
    elif score >= 30:
        level = "Bronze"
        level_desc = "Attention : plusieurs signaux négatifs. Essaie de remonter ton score."
        level_color = "warning"
    else:
        level = "Critique"
        level_desc = "Ton compte est à risque. Respecte strictement les règles pour remonter."
        level_color = "danger"

    # 🔎 Filtre de période
    period = request.GET.get("period", "90")  # par défaut : 90 jours
    now = timezone.now()

    logs_qs = ProviderPenaltyLog.objects.filter(provider=user)

    if period != "all":
        try:
            days = int(period)
        except ValueError:
            days = 90
        start_date = now - timedelta(days=days)
        logs_qs = logs_qs.filter(created_at__gte=start_date)

    logs_qs = logs_qs.order_by("-created_at")

    # On limite l'affichage principal (mais pas l'export)
    logs = list(logs_qs[:100])

    total_change = logs_qs.aggregate_sum = sum(l.amount for l in logs_qs)
    total_penalties = logs_qs.filter(amount__lt=0).count()
    total_positive = logs_qs.filter(amount__gt=0).count()
    last_change = logs[0] if logs else None

    context = {
        "profile": profile,
        "score": score,
        "level": level,
        "level_desc": level_desc,
        "level_color": level_color,
        "logs": logs,
        "total_change": total_change,
        "total_penalties": total_penalties,
        "total_positive": total_positive,
        "last_change": last_change,
        "period": period,
    }
    return render(request, "accounts/trust_score_dashboard.html", context)

@provider_required
@profile_completion_required
def trust_score_export_html_view(request):
    """
    Télécharge l'historique complet du trust score au format HTML stylé.
    """
    user = request.user

    logs = (
        ProviderPenaltyLog.objects
        .filter(provider=user)
        .order_by("-created_at")
    )

    score = getattr(user.profile, "trust_score", 0) or 0

    html = render(
        request,
        "accounts/trust_score_export.html",
        {
            "user": user,
            "score": score,
            "logs": logs,
        },
    ).content

    filename = f"historique-trust-score-{user.username}.html"

    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from services.models import ProviderPenaltyLog  # adapte si besoin
from accounts.decorators import provider_required

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors


@provider_required
@login_required
@profile_completion_required
def trust_score_export_pdf_view(request):
    """
    Génère un PDF pro avec :
      - infos prestataire
      - score actuel
      - historique des changements de trust_score
    """
    user = request.user
    profile = getattr(user, "profile", None)

    # Récupérer les logs
    logs = (
        ProviderPenaltyLog.objects
        .filter(provider=user)
        .order_by("created_at")
    )

    # Préparer la réponse HTTP
    filename = f"historique_trust_score_{user.username}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    # Création du PDF
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Marges
    margin_left = 2 * cm
    margin_right = width - 2 * cm
    y = height - 2 * cm

    # ---- En-tête ----
    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin_left, y, "Historique du score de confiance")
    y -= 1 * cm

    p.setFont("Helvetica", 10)
    full_name = profile.full_name or user.get_username()
    p.drawString(margin_left, y, f"Prestataire : {full_name}")
    y -= 0.5 * cm

    p.drawString(margin_left, y, f"Email : {user.email or '-'}")
    y -= 0.5 * cm

    p.drawString(margin_left, y, f"Score actuel : {profile.trust_score}/100")
    y -= 1 * cm

    # Ligne de séparation
    p.setStrokeColor(colors.grey)
    p.line(margin_left, y, margin_right, y)
    y -= 0.8 * cm

    # ---- Titre du tableau ----
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin_left, y, "Historique des événements")
    y -= 0.8 * cm

    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin_left, y, "Date")
    p.drawString(margin_left + 5 * cm, y, "Changement")
    p.drawString(margin_left + 8 * cm, y, "Raison")
    y -= 0.5 * cm

    p.setStrokeColor(colors.lightgrey)
    p.line(margin_left, y, margin_right, y)
    y -= 0.4 * cm

    p.setFont("Helvetica", 9)

    def new_page_footer_header(canvas_obj):
        """Quand on change de page, on redessine l’en-tête du tableau."""
        nonlocal y
        canvas_obj.showPage()
        canvas_obj.setFont("Helvetica", 9)
        y = height - 2 * cm

        canvas_obj.setFont("Helvetica-Bold", 12)
        canvas_obj.drawString(margin_left, y, "Historique des événements (suite)")
        y -= 0.8 * cm

        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(margin_left, y, "Date")
        canvas_obj.drawString(margin_left + 5 * cm, y, "Changement")
        canvas_obj.drawString(margin_left + 8 * cm, y, "Raison")
        y -= 0.5 * cm

        canvas_obj.setStrokeColor(colors.lightgrey)
        canvas_obj.line(margin_left, y, margin_right, y)
        y -= 0.4 * cm

        canvas_obj.setFont("Helvetica", 9)

    if logs.exists():
        for log in logs:
            # Si on arrive trop bas, nouvelle page
            if y < 2 * cm:
                new_page_footer_header(p)

            date_str = log.created_at.strftime("%d/%m/%Y %H:%M")
            change_str = f"{'+' if log.amount > 0 else ''}{log.amount}"
            reason = log.reason or ""

            # On tronque la raison si elle est trop longue
            max_chars = 70
            if len(reason) > max_chars:
                reason = reason[:max_chars - 3] + "..."

            p.drawString(margin_left, y, date_str)
            p.drawString(margin_left + 5 * cm, y, change_str)
            p.drawString(margin_left + 8 * cm, y, reason)
            y -= 0.5 * cm
    else:
        p.drawString(margin_left, y, "Aucun événement enregistré pour l’instant.")
        y -= 0.5 * cm

    # Fin du document
    p.showPage()
    p.save()
    return response


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Subscription, SubscriptionPlan






@login_required
def success_stories_view(request):
    """Affiche la page des Success Stories"""
    # Exemple : tu peux récupérer les profils vérifiés ayant un bon score
    top_students = Profile.objects.filter(role="student", trust_score__gte=80).order_by('-trust_score')[:3]
    top_providers = Profile.objects.filter(role="provider", is_service_provider_verified=True).order_by('-trust_score')[:3]
    companies = Profile.objects.filter(role="company", company_verified=True)[:3]
    reviews = StageReview.objects.filter().order_by('-created_at')[:10]
    reviewes = ServiceReview.objects.filter().order_by('-created_at')[:10]


    context = {
        "top_students": top_students,
        "top_providers": top_providers,
        "companies": companies,
        'reviews': reviews,
        'reviewses': reviewes,
    }
    return render(request, "pages/success_stories.html", context)



# accounts/views.py
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
@profile_completion_required
def dashboard_access_view(request):
    user = request.user
    
    # On vérifie si l'utilisateur a un profil
    if not hasattr(user, 'profile'):
        # Cas rare : user sans profil -> on peut le rediriger vers la création de profil ou l'accueil
        return redirect('home') 

    role = user.profile.role

    if role == 'student':
        return redirect('student_dashboard') # Assure-toi que ce 'name' existe dans tes urls
    elif role == 'company':
        return redirect('company_dashboard')
    elif role == 'provider': # ou 'prestataire' selon ta base de données
        return redirect('provider_dashboard')
    elif user.is_superuser or user.is_staff:
        return redirect('admin:index')
    
    # Par défaut si aucun rôle ne matche
    return redirect('home')


# --- IMPORTS NÉCESSAIRES ---
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
import os

# Pour la génération d'image
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
from stages.models import StudentDocument

# Importe tes modèles
from .models import Profile # Adapte les imports


# ==========================================
# 1. CHOISIR LE DOCUMENT ACTIF
# ==========================================
@login_required
def set_qr_document(request, doc_id):
    """Définit quel document est lié au QR code du profil."""
    document = get_object_or_404(StudentDocument, id=doc_id, user=request.user)
    profile = request.user.profile
    
    profile.qr_target_document = document
    profile.save()
    
    messages.success(request, f"Votre QR Code pointe maintenant vers : {document.title}")
    return redirect('student_documents_list') # Retour à la liste


# ==========================================
# 2. LA REDIRECTION INTELLIGENTE (L'URL du QR)
# ==========================================
def qr_redirect_view(request, username):
    """
    URL publique scannée par le QR Code.
    Trouve le profil et redirige vers le document choisi actuellement.
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    if profile.qr_target_document and profile.qr_target_document.file:
        # Redirection vers le fichier média actuel
        return redirect(profile.qr_target_document.file.url)
    else:
        # Page d'erreur si aucun document n'est configuré
        return HttpResponse("Cet étudiant n'a pas encore configuré son portfolio.", status=404)

import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required

@login_required
def generate_campus_pass_view(request):
    profile = request.user.profile
    
    # --- 1. CONFIGURATION DES COULEURS (TEXT_DARK défini ici) ---
    TEXT_DARK = (15, 23, 42)    # Bleu Ardoise très foncé
    NAVY = (23, 37, 84)         # Bleu Nuit (Vague principale)
    CYAN = (6, 182, 212)        # Cyan (Ligne décorative)
    WHITE = (255, 255, 255)
    GRAY_LIGHT = (241, 245, 249)

    # Dimensions pour une haute résolution
    CARD_WIDTH, CARD_HEIGHT = 1050, 600
    
    # Création de la base
    card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), WHITE)
    # Image temporaire pour l'anti-aliasing (courbes lisses)
    overlay = Image.new('RGBA', (CARD_WIDTH * 2, CARD_HEIGHT * 2), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # --- 2. DESSIN DU DESIGN (Vagues haut-droite) ---
    # Coordonnées doublées pour l'overlay puis redimensionnées (super-sampling)
    # Vague principale Bleu Nuit
    draw_ov.ellipse([850, -600, 2400, 500], fill=NAVY)
    # Ligne Cyan
    draw_ov.arc([820, -620, 2430, 530], start=0, end=360, fill=CYAN, width=25)

    # Redimensionnement et collage sur la carte
    overlay = overlay.resize((CARD_WIDTH, CARD_HEIGHT), resample=Image.Resampling.LANCZOS)
    card.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(card)

    # --- 3. GESTION DES POLICES ---
    try:
        # Tente de charger les polices système (Arial ou similaire)
        font_bold = ImageFont.truetype("arialbd.ttf", 55)
        font_medium = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 26)
    except:
        font_bold = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # --- 4. LOGO / AVATAR (À GAUCHE) ---
    if profile.avatar:
        avatar_size = (240, 240)
        avatar_img = Image.open(profile.avatar.path).convert("RGBA")
        avatar_img = ImageOps.fit(avatar_img, avatar_size, method=Image.Resampling.LANCZOS)
        
        # Masque rond
        mask = Image.new('L', avatar_size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + avatar_size, fill=255)
        card.paste(avatar_img, (100, 140), mask)
    else:
        # Monogramme "CH" stylisé
        draw.line([(100, 140), (100, 280)], fill=NAVY, width=12)
        draw.text((120, 165), "CH", font=font_bold, fill=NAVY)

    # --- 5. NOM ET TITRE (CENTRE DROITE) ---
    x_pos = 460
    full_name = profile.full_name if profile.full_name else request.user.username
    draw.text((x_pos, 220), full_name.upper(), font=font_bold, fill=TEXT_DARK)
    
    job_title = profile.student_field or "Candidat CampusHub"
    draw.text((x_pos, 290), job_title, font=font_medium, fill=CYAN)

    # --- 6. INFOS DE CONTACT AVEC ICÔNES DESSINÉES ---
    y_contact = 370
    
    # Fonction pour dessiner des icônes simples (garantit la visibilité)
    def draw_contact_line(draw_obj, x, y, type, text):
        # Icône Téléphone (petit rectangle)
        if type == "phone":
            draw_obj.rectangle([x, y+5, x+15, y+25], outline=TEXT_DARK, width=2)
            draw_obj.point([x+7, y+22], fill=TEXT_DARK)
        # Icône Email (enveloppe)
        elif type == "email":
            draw_obj.rectangle([x, y+5, x+22, y+20], outline=TEXT_DARK, width=2)
            draw_obj.line([x, y+5, x+11, y+12, x+22, y+5], fill=TEXT_DARK, width=2)
        # Icône Web (globe simplifié)
        elif type == "web":
            draw_obj.ellipse([x, y+5, x+20, y+25], outline=TEXT_DARK, width=2)
            draw_obj.line([x+10, y+5, x+10, y+25], fill=TEXT_DARK, width=1)
        
        draw_obj.text((x + 40, y), text, font=font_small, fill=TEXT_DARK)

    draw_contact_line(draw, x_pos, y_contact, "phone", profile.phone or "+237 600 000 000")
    draw_contact_line(draw, x_pos, y_contact + 45, "email", request.user.email)
    draw_contact_line(draw, x_pos, y_contact + 90, "web", "www.campushub.me")

    # --- 7. QR CODE (BAS GAUCHE) ---
    qr_url = request.build_absolute_uri(reverse('qr_redirect_view', args=[request.user.username]))
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=NAVY, back_color="white").convert('RGB')
    qr_img = qr_img.resize((140, 140))
    
    # Placement discret
    card.paste(qr_img, (100, 410))
    draw.text((100, 555), "@campushub_network", font=font_small, fill=TEXT_DARK)

    # --- 8. RÉPONSE ---
    response = HttpResponse(content_type="image/png")
    response['Content-Disposition'] = f'inline; filename="campus_pass_{request.user.username}.png"'
    card.save(response, 'PNG')
    return response


@login_required
@require_POST
def update_onboarding_status(request):
    """Met à jour la préférence d'onboarding de l'utilisateur."""
    show = request.POST.get('show_onboarding') == 'true'
    profile = request.user.profile
    profile.show_onboarding = show
    profile.onboarding_completed = True
    profile.save()
    return JsonResponse({'status': 'success'})

@login_required
def subscription_plans_view(request):
    """Affiche les plans disponibles correspondant au rôle de l'utilisateur."""
    from .services import UsageManager
    
    # Filtrage par rôle
    role = getattr(request.user.profile, 'role', 'student')
    plans = SubscriptionPlan.objects.filter(role_target=role, is_active=True).order_by('price')
    
    usage_stats = UsageManager.get_usage_stats(request.user)
    subscription = getattr(request.user, 'user_subscription', None)
    
    return render(request, 'accounts/subscription_plans.html', {
        'plans': plans,
        'usage_stats': usage_stats,
        'subscription': subscription,
    })

@login_required
def subscribe_view(request, plan_id):
    """Redirige vers le paiement pour s'abonner à un plan."""
    from django.urls import reverse
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # Si le plan est gratuit, on l'active directement (ou on refuse si déjà un plan premium)
    if plan.price == 0:
        messages.info(request, "Ce plan est gratuit.")
        return redirect('subscription_plans')

    # Redirection vers l'initialisation du paiement
    return redirect(f"{reverse('payments:initiate_payment')}?plan_id={plan.id}&amount={plan.price}")

from django.http import JsonResponse
