# accounts/decorators.py

from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(allowed_roles):
    """
    Vérifie que l'utilisateur a un rôle parmi allowed_roles.
    Exemple : @role_required(['student', 'company'])
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Si pas connecté → on laisse login_required gérer ça
            if not request.user.is_authenticated:
                return redirect('login')

            profile = getattr(request.user, 'profile', None)
            if profile is None or profile.role not in allowed_roles:
                messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
                return redirect('home')  # page d'accueil ou autre

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# Décorateurs pratiques
def student_required(view_func):
    decorated_view_func = login_required(role_required(['student'])(view_func))
    return decorated_view_func


def company_required(view_func):
    decorated_view_func = login_required(role_required(['company'])(view_func))
    return decorated_view_func

# accounts/decorators.py

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def _get_profile(user):
    """
    Helper pour récupérer le profil sans planter si il n'existe pas.
    """
    return getattr(user, "profile", None)


# --------------------------------------------------------------------
# 1) not_banned_required : blocage global des comptes bannis
# --------------------------------------------------------------------
def not_banned_required(view_func):
    """
    Empêche les utilisateurs bannis (profile.is_banned == True) d'accéder à la vue.
    À utiliser sur les vues sensibles (services, messagerie, stages, etc.).
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        profile = _get_profile(user)

        if not user.is_active:
            messages.error(request, "Votre compte est inactif. Contactez le support.")
            return redirect("home")

        if profile and getattr(profile, "is_banned", False):
            messages.error(request, "Votre compte est banni. Accès refusé.")
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return _wrapped


# --------------------------------------------------------------------
# 2) basic_profile_required : profil léger (pour services, etc.)
#    → pour les utilisateurs qui ne veulent PAS forcément utiliser
#      les modules stages / orientation, mais doivent avoir un minimum.
# --------------------------------------------------------------------
def basic_profile_required(view_func):
    """
    Vérifie que l'utilisateur a un profil minimum rempli (sans exiger
    les infos spécifiques à l'orientation ou aux stages).

    Idéal pour :
      - module Services (prestations)
      - modules généraux du site
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        profile = _get_profile(user)

        if not user.is_active:
            messages.error(request, "Votre compte est inactif. Contactez le support.")
            return redirect("home")

        if profile and getattr(profile, "is_banned", False):
            messages.error(request, "Votre compte est banni. Accès refusé.")
            return redirect("home")

        # On suppose que ces champs existent dans ton Profile
        # Adapte les noms si nécessaire : full_name, phone, city...
        missing_fields = []
        if profile:
            if not getattr(profile, "full_name", "").strip():
                missing_fields.append("nom complet")
            if not getattr(profile, "phone", "").strip():
                missing_fields.append("numéro de téléphone")
            # Ville facultative, tu peux l'ajouter si tu veux la rendre obligatoire
            # if not getattr(profile, "city", "").strip():
            #     missing_fields.append("ville")

        if missing_fields:
            messages.warning(
                request,
                "Complétez votre profil pour continuer (champs manquants : "
                + ", ".join(missing_fields)
                + ")."
            )
            return redirect("profile_edit")

        return view_func(request, *args, **kwargs)

    return _wrapped


# --------------------------------------------------------------------
# 3) profile_complete_required : profil plus strict (pour stages/orientation)
# --------------------------------------------------------------------
def profile_complete_required(view_func):
    """
    Vérifie que le profil est COMPLET, pour les modules exigeants
    (ex : Stages, Orientation).

    Tu peux rendre obligatoires :
      - nom complet
      - téléphone
      - ville
      - niveau d'étude
      - etc.
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        profile = _get_profile(user)

        if not user.is_active:
            messages.error(request, "Votre compte est inactif.")
            return redirect("home")

        if profile and getattr(profile, "is_banned", False):
            messages.error(request, "Votre compte est banni. Accès refusé.")
            return redirect("home")

        if not profile:
            messages.warning(request, "Veuillez compléter votre profil avant d'accéder à cette page.")
            return redirect("profile_edit")

        # Liste des champs obligatoires pour un profil "complet"
        required_fields = [
            ("full_name", "nom complet"),
            ("phone", "numéro de téléphone"),
            ("city", "ville"),
            # Tu peux ajouter ici :
            # ("current_level", "niveau d'étude"),
            # ("orientation_result", "orientation"),
        ]

        missing = []
        for field_name, label in required_fields:
            value = getattr(profile, field_name, None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append(label)

        if missing:
            messages.warning(
                request,
                "Complétez votre profil avant d'utiliser cette fonctionnalité "
                "(champs manquants : " + ", ".join(missing) + ")."
            )
            return redirect("profile_edit")

        return view_func(request, *args, **kwargs)

    return _wrapped


# --------------------------------------------------------------------
# 4) provider_required : accès au rôle de PRESTATAIRE (services)
#     → n'importe quel user peut être provider, mais on force :
#       - non banni
#       - profil léger complet
# --------------------------------------------------------------------
# accounts/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def provider_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        profile = getattr(user, "profile", None)

        if not user.is_active:
            messages.error(request, "Votre compte est inactif. Contactez le support.")
            return redirect("home")

        if not profile:
            messages.error(request, "Votre profil est incomplet. Merci de le compléter.")
            return redirect("profile_edit")

        # Banni ?
        if getattr(profile, "is_banned", False):
            messages.error(request, "Votre compte est banni. Vous ne pouvez pas offrir de services.")
            return redirect("home")

        # ❌ Pas prestataire
        if not profile.is_service_provider:
            messages.error(
                request,
                "Désolé, vous n'êtes pas connecté avec un compte prestataire. "
                "Activez l’option « Je veux proposer des services » dans votre profil."
            )
            return redirect("profile_edit")

        # ⚠️ Prestataire mais PAS encore vérifié
        if not getattr(profile, "is_service_provider_verified", False):
            messages.warning(
                request,
                "Vous êtes connecté en tant que prestataire, "
                "mais veuillez attendre la vérification de votre compte par les admins "
                "avant d’accéder à cette page."
            )
            return redirect("profile_edit")

        # ✅ Tout est OK
        return view_func(request, *args, **kwargs)

    return _wrapped
# --------------------------------------------------------------------
# 5) client_required : accès au rôle de CLIENT (commande de services)
# --------------------------------------------------------------------
def client_required(view_func):
    """
    Pour les vues où l'utilisateur agit comme CLIENT dans le module Services
    (passer une commande, voir ses commandes, etc.).

    N'importe quel user peut être client, mais :
      - compte actif
      - non banni
    (tu peux ici réutiliser basic_profile_required si tu veux aussi
     forcer le téléphone côté client).
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        profile = _get_profile(user)

        if not user.is_active:
            messages.error(request, "Votre compte est inactif.")
            return redirect("home")

        if profile and getattr(profile, "is_banned", False):
            messages.error(request, "Votre compte est banni. Vous ne pouvez pas passer de commande.")
            return redirect("home")

        # Si tu veux aussi exiger un téléphone côté client, décommente :
        if not getattr(profile, "phone", "").strip():
            messages.warning(
                request,
                "Veuillez ajouter un numéro de téléphone à votre profil avant de passer une commande."
            )
            return redirect("profile_edit")

        return view_func(request, *args, **kwargs)

    return _wrapped


from django.contrib import messages
from django.shortcuts import redirect


def plus_required(view_func):
    """Autorise seulement les comptes Plus ou Premium"""
    def _wrapped_view(request, *args, **kwargs):
        sub = getattr(request.user, "subscription", None)
        if not sub or not (sub.is_plus or sub.is_premium):
            messages.error(request, "🚀 Cette fonctionnalité est réservée aux membres Plus.")
            return redirect("subscription_plans")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def premium_required(view_func):
    """Autorise seulement les comptes Premium"""
    def _wrapped_view(request, *args, **kwargs):
        sub = getattr(request.user, "subscription", None)
        if not sub or not sub.is_premium:
            messages.error(request, "👑 Cette fonctionnalité est réservée aux membres Premium.")
            return redirect("subscription_plans")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# companies/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def company_subscription_required(view_func):
    """Bloque les entreprises sans abonnement actif (système unifié)"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.profile.role != "company":
            messages.error(request, "Accès réservé aux entreprises.")
            return redirect("home")

        # Utilisation du système de souscription unifié
        sub = getattr(request.user, "user_subscription", None)
        if not sub or not sub.is_active or sub.is_expired:
            messages.warning(request, "⚠️ Votre abonnement est expiré ou inexistant.")
            return redirect("company_subscription_plans")
        
        # On vérifie aussi que le plan correspond bien au rôle company (sécurité supp)
        if sub.plan and sub.plan.role_target != 'company':
            messages.error(request, "Abonnement invalide pour ce profil.")
            return redirect("company_subscription_plans")

        return view_func(request, *args, **kwargs)
    return _wrapped_view



# decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def profile_completion_required(view_func):
    """
    Assure que le profil est rempli selon le rôle avant d'accéder à la vue.
    Redirige vers 'profile_edit' avec un message détaillé en cas d'échec.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        profile = request.user.profile
        is_complete, missing_fields = profile.get_completion_status()

        if not is_complete:
            if "role" in missing_fields:
                messages.error(request, "Veuillez d'abord choisir votre rôle (Étudiant, Entreprise ou Prestataire).")
            else:
                fields_str = ", ".join(missing_fields)
                messages.warning(request, f"Profil incomplet ! Champs requis : {fields_str}")
            
            return redirect('profile_edit')

        return view_func(request, *args, **kwargs)

    return _wrapped_view