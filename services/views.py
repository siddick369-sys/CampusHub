from datetime import datetime, timedelta
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth import get_user_model


from .utils_emails import notify_service_provider_new_urgent_order, send_subscription_changed_email

from .utils_subscriptions import *

from .utils_slots import get_service_slots_for_date

# Create your views here.
# si tu as déjà un util pour les PDF dans stages :
try:
    from stages.utils_pdf import render_html_to_pdf_bytes  # adapte au nom réel de ta fonction
except ImportError:
    render_html_to_pdf_bytes = None

from django.db.models import Q, Exists, OuterRef, BooleanField, Value

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q,F,Case, When,IntegerField
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .utils_availability import get_provider_availability_status

from .utils_notifications import notify_client_order_status_change, notify_clients_service_deactivated, notify_provider_order_status_change, notify_service_provider_new_order, notify_users_for_new_service_matching_alerts

from .models import ServiceCallSession, ServiceMedia, ServiceOffer, ServiceCategory, ServicePackage, ServiceTag, ServiceOrder
from accounts.decorators import provider_required, client_required, basic_profile_required, not_banned_required
from django.contrib.auth.decorators import login_required
from .models import ServiceOffer, ServiceOrder, ServiceSearchAlert
from .models import (
    ServiceOffer,
    ServiceOrder,
    ServiceReview,
    ServiceOrderReport,
    # ... le reste ...
)
from .forms import ServiceReviewForm, ServiceOrderReportForm
from django.utils import timezone
MAX_OPEN_REPORTS_FOR_REVIEW = 3  # au-delà de 3 signalements ouverts, on bloque les avis



@login_required
def services_test_view(request):
    """
    Page de test pour le module Services.
    Permet d'accéder rapidement à toutes les fonctionnalités.
    """
    user = request.user
    profile = getattr(user, "profile", None)

    my_services = ServiceOffer.objects.filter(provider=user)
    my_orders_as_provider = ServiceOrder.objects.filter(provider=user).order_by("-created_at")[:5]
    my_orders_as_client = ServiceOrder.objects.filter(client=user).order_by("-created_at")[:5]
    my_alerts = ServiceSearchAlert.objects.filter(user=user)

    context = {
        "profile": profile,
        "my_services": my_services,
        "my_orders_as_provider": my_orders_as_provider,
        "my_orders_as_client": my_orders_as_client,
        "my_alerts": my_alerts,
    }
    return render(request, "services/services_test.html", context)
# Critères pour "Top prestataire"
from django.db.models import Q, Exists, OuterRef, Value, BooleanField, F
from django.shortcuts import render
from .models import ServiceOffer, ServiceCategory, ServiceTag, FavoriteService
from .utils_availability import get_provider_availability_status

TOP_PROVIDER_MIN_TRUST = 80
TOP_PROVIDER_MIN_RATING = 4.5
TOP_PROVIDER_MIN_RATING_COUNT = 5
MIN_TRUST_TO_PUBLISH_SERVICE = 20


def service_list_view(request):
    """
    Liste des services avec filtres avancés + badges top prestataire + favoris + dispo.
    On NE montre que les services dont le prestataire :
      - est bien marqué comme prestataire
      - a un trust_score défini
      - a un trust_score >= MIN_TRUST_TO_PUBLISH_SERVICE
    """
    # ---------- BASE QUERYSET ----------
    services = (
        ServiceOffer.objects.filter(
            status="active",
            visibility="public",
        )
        .select_related("provider", "category", "provider__profile")
        .prefetch_related("tags")
        .annotate(
            provider_trust=F("provider__profile__trust_score"),
            provider_is_service_provider=F("provider__profile__is_service_provider"),
        )
    )

    # 🔒 Filtre global : on enlève tous les prestataires douteux
    services = services.filter(
        provider_is_service_provider=True,
        provider_trust__gte=MIN_TRUST_TO_PUBLISH_SERVICE,
    )

    # ---------- RÉCUP DES FILTRES GET ----------
    q = (request.GET.get("q") or "").strip()
    category_slug = (request.GET.get("category") or "").strip()
    tag_slug = (request.GET.get("tag") or "").strip()
    min_price = (request.GET.get("min_price") or "").strip()
    max_price = (request.GET.get("max_price") or "").strip()
    min_days = (request.GET.get("min_days") or "").strip()
    max_days = (request.GET.get("max_days") or "").strip()
    currency = (request.GET.get("currency") or "").strip()
    provider_city = (request.GET.get("provider_city") or "").strip()

    # Filtres « prestataire de confiance »
    verified_only = request.GET.get("verified_only") == "1"
    top_only = request.GET.get("top_only") == "1"
    min_rating_raw = (request.GET.get("min_rating") or "").strip()
    min_rating_val = None

    # ---------- MOT-CLE ----------
    if q:
        services = services.filter(
            Q(title__icontains=q)
            | Q(short_description__icontains=q)
            | Q(description__icontains=q)
            | Q(provider__username__icontains=q)
            | Q(provider__email__icontains=q)
        )

    # ---------- CAT / TAG ----------
    if category_slug:
        services = services.filter(category__slug=category_slug)

    if tag_slug:
        services = services.filter(tags__slug=tag_slug)

    # ---------- PRIX ----------
    if min_price.isdigit():
        services = services.filter(price_min__gte=int(min_price))
    if max_price.isdigit():
        services = services.filter(price_max__lte=int(max_price))

    # ---------- DÉLAIS ----------
    if min_days.isdigit():
        services = services.filter(delivery_time_min_days__gte=int(min_days))
    if max_days.isdigit():
        services = services.filter(delivery_time_max_days__lte=int(max_days))

    # ---------- DEVISE ----------
    if currency:
        services = services.filter(currency__iexact=currency)

    # ---------- VILLE ----------
    if provider_city:
        services = services.filter(provider__profile__city__icontains=provider_city)

    # ---------- NOTE MINI ----------
    if min_rating_raw:
        try:
            min_rating_val = float(min_rating_raw.replace(",", "."))
            services = services.filter(average_rating__gte=min_rating_val)
        except ValueError:
            min_rating_val = None

    # ---------- PRESTATAIRES VÉRIFIÉS ----------
    if verified_only:
        services = services.filter(provider__profile__is_service_provider_verified=True)

    # ---------- TOP PRESTATAIRES (filtre) ----------
    if top_only:
        services = services.filter(
            average_rating__gte=TOP_PROVIDER_MIN_RATING,
            rating_count__gte=TOP_PROVIDER_MIN_RATING_COUNT,
            provider__profile__trust_score__gt=TOP_PROVIDER_MIN_TRUST,
            provider__profile__is_service_provider_verified=True,
        )

    services = services.order_by("-is_featured", "-created_at").distinct()

    # ---------- IDS TOP PRESTATAIRE (pour badge) ----------
    top_service_ids = list(
        services.filter(
            average_rating__gte=TOP_PROVIDER_MIN_RATING,
            rating_count__gte=TOP_PROVIDER_MIN_RATING_COUNT,
            provider__profile__trust_score__gt=TOP_PROVIDER_MIN_TRUST,
            provider__profile__is_service_provider_verified=True,
        ).values_list("id", flat=True)
    )

    # ---------- DISPONIBILITÉ PRESTATAIRE ----------
    service_availability = {}
    for s in services:
        code, label = get_provider_availability_status(s.provider)
        s.availability_code = code
        s.availability_label = label
        service_availability[s.id] = (code, label)

    # ---------- FAVORIS ----------
    favorite_services = []
    if request.user.is_authenticated:
        favorite_subquery = FavoriteService.objects.filter(
            user=request.user,
            service_id=OuterRef("pk"),
        )
        services = services.annotate(
            is_favorite=Exists(favorite_subquery)
        )

        fav_qs = (
            FavoriteService.objects.filter(user=request.user)
            .select_related("service")
            .order_by("-created_at")
        )
        favorite_services = [f.service for f in fav_qs]
    else:
        services = services.annotate(
            is_favorite=Value(False, output_field=BooleanField())
        )

    # ---------- LOGIQUE D'ALERTE (SI VIDE) ----------
    if not services.exists() and request.user.is_authenticated and (q or category_slug or min_price or max_price or provider_city):
        from accounts.services import UsageManager
        if UsageManager.is_action_allowed(request.user, 'search_alerts_count'):
            from .models import ServiceSearchAlert, ServiceCategory
            category_obj = None
            if category_slug:
                category_obj = ServiceCategory.objects.filter(slug=category_slug).first()
            
            alert, created = ServiceSearchAlert.objects.get_or_create(
                user=request.user,
                q=q,
                category=category_obj,
                min_price=int(min_price) if min_price.isdigit() else None,
                max_price=int(max_price) if max_price.isdigit() else None,
                provider_city=provider_city,
                defaults={'is_active': True}
            )
            if created:
                messages.info(request, "Aucun service ne correspond. Une alerte de recherche a été créée.")
        else:
            messages.warning(request, "Quota d'alertes de recherche atteint (voir vos plans).")

    categories = ServiceCategory.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )
    tags = ServiceTag.objects.all().order_by("name")

    context = {
        "services": services,
        "categories": categories,
        "tags": tags,
        "favorite_services": favorite_services,
        "service_availability": service_availability,
        "top_service_ids": top_service_ids,
        "verified_only": verified_only,
        "top_only": top_only,
        "filters": {
            "q": q,
            "category": category_slug,
            "tag": tag_slug,
            "min_price": min_price,
            "max_price": max_price,
            "min_days": min_days,
            "max_days": max_days,
            "currency": currency,
            "provider_city": provider_city,
            "min_rating": min_rating_raw,
            "verified_only": verified_only,
            "top_only": top_only,
        },
    }
    return render(request, "services/service_list.html", context)
@login_required
def service_detail_view(request, slug):
    """
    Détail d’un service. Accessible à tout utilisateur connecté.
    """
    service = get_object_or_404(
        ServiceOffer.objects.select_related("provider", "category"),
        slug=slug,
        status__in=["active", "paused"],  # visible, même si non commandable
    )

    # ... ce que tu avais déjà ...

    packages = service.packages.filter(is_active=True).order_by("sort_order", "price")
    extras = service.extras.filter(is_active=True).order_by("price")


    user = request.user

    # On ne peut pas commander son propre service
    is_owner = (service.provider_id == user.id)
    can_order = (
        service.status == "active"
        and not is_owner
        and user.is_authenticated
    )
    # 🔹 Créneaux actifs liés à ce prestataire (+ optionnellement à ce service)
    slots = ProviderTimeSlot.objects.filter(
    provider=service.provider,).filter(
    Q(service__isnull=True) | Q(service=service)).order_by("weekday", "start_time")

    # Simple "prochain créneau" = le premier dans la liste
    next_slot = slots.first()
    availability_code,availability_label = get_provider_availability_status(service.provider)
    # 🔎 SERVICES SIMILAIRES (catégorie + tags, puis fallback sur tags seuls, puis top services)
    base_qs = (
        ServiceOffer.objects
        .filter(
            status="active",
            visibility="public",
        )
        .exclude(id=service.id)
        .select_related("provider", "category", "provider__profile")
        .prefetch_related("tags")
    )

    tag_ids = list(service.tags.values_list("id", flat=True))

    similar_qs = base_qs

    # 1) Si le service a une catégorie : on filtre d'abord par catégorie
    if service.category:
        similar_qs = similar_qs.filter(category=service.category)

    # 2) Si le service a des tags : on filtre par tags en commun
    if tag_ids:
        similar_qs = similar_qs.filter(tags__in=tag_ids)

    similar_qs = similar_qs.distinct()

    # 3) Fallback : si après tout ça il ne reste presque rien (0 ou 1), 
    # on prend d'autres services "top" basés sur les tags uniquement, 
    # même dans d'autres catégories.
    if similar_qs.count() <= 1 and tag_ids:
        similar_qs = (
            base_qs
            .filter(tags__in=tag_ids)
            .distinct()
        )

    # 4) Si on n'a toujours rien → on propose quelques "Top prestataires" globaux
    if not similar_qs.exists():
        similar_qs = (
            base_qs
            .filter(
                provider__profile__trust_score__gte=80,
                average_rating__gte=4.5,
                rating_count__gte=5,
                provider__profile__is_service_provider_verified=True,
            )
        )

    # 🔢 Tri final par confiance & note
    similar_qs = similar_qs.annotate(
        provider_trust=F("provider__profile__trust_score"),
    ).order_by(
        Case(
            When(provider_trust__isnull=True, then=1),
            default=0,
            output_field=IntegerField(),
        ),
        F("provider_trust").desc(nulls_last=True),
        F("average_rating").desc(nulls_last=True),
        F("rating_count").desc(nulls_last=True),
        "-created_at",
    ).distinct()

    # 📄 Pagination des services similaires (4 par page)
    sim_page_number = request.GET.get("sim_page") or 1
    sim_paginator = Paginator(similar_qs, 4)
    similar_services_page = sim_paginator.get_page(sim_page_number)
    is_following = False
    followers_count = 0
    
    provider = service.provider
    is_following = ProviderFollow.objects.filter(
        client=request.user,
        provider=provider,
    ).exists()
    followers_count= ProviderFollow.objects.filter(provider=provider).count()
        

    provider_reviews = ServiceReview.objects.filter(
        service__provider=service.provider
    ).select_related("client", "service").order_by("-created_at")

    # Calcul de la distribution des notes pour le prestataire (tous ses services)
    from django.db.models import Count
    rating_stats = provider_reviews.aggregate(
        total=Count('id'),
        star5=Count('id', filter=Q(rating=5)),
        star4=Count('id', filter=Q(rating=4)),
        star3=Count('id', filter=Q(rating=3)),
        star2=Count('id', filter=Q(rating=2)),
        star1=Count('id', filter=Q(rating=1)),
    )
    
    # Calcul des pourcentages pour le graph
    total_reviews = rating_stats['total'] or 1
    rating_dist = {
        5: (rating_stats['star5'] / total_reviews) * 100,
        4: (rating_stats['star4'] / total_reviews) * 100,
        3: (rating_stats['star3'] / total_reviews) * 100,
        2: (rating_stats['star2'] / total_reviews) * 100,
        1: (rating_stats['star1'] / total_reviews) * 100,
    }

    context = {
        "service": service,
        "similar_services_page":similar_services_page,
        "can_order": can_order,
        "is_owner": is_owner,
        "availability_code":availability_code,
        "availability_label":availability_label,
        "packages": packages,
        "extras": extras,
        "slots":slots,
        "next_slot":next_slot,
        "is_following":is_following,
        "followers_count":followers_count,
        "provider_reviews": provider_reviews,
        "rating_stats": rating_stats,
        "rating_dist": rating_dist,
    }
    return render(request, "services/service_detail.html", context)
from .models import ServiceOffer, ServiceCategory, ServiceTag, ServiceOrder, ServiceSearchAlert
from django.contrib.auth.decorators import login_required
@login_required
def service_search_alert_list_view(request):
    alerts = ServiceSearchAlert.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "services/service_search_alert_list.html", {
        "alerts": alerts,
    })
@login_required
def service_search_alert_delete_view(request, alert_id):
    alert = get_object_or_404(ServiceSearchAlert, id=alert_id, user=request.user)
    alert.delete()
    messages.success(request, "Votre alerte de recherche a été supprimée.")
    return redirect("service_search_alert_list")
from accounts.decorators import provider_required

@provider_required
def provider_dashboard_view(request):
    """
    Tableau de bord d’un prestataire :
      - ses services
      - ses commandes en tant que prestataire
    """
    user = request.user

    services = ServiceOffer.objects.filter(provider=user).order_by("-created_at")
    current_plan = get_provider_current_plan(user)
    usage = get_provider_service_usage(user)


    orders = ServiceOrder.objects.filter(provider=user).select_related("service", "client").order_by("-created_at")

    context = {
        "services": services,
        "orders": orders,
        "current_plan": current_plan,
        "plan_usage": usage,
    }
    return render(request, "services/provider_dashboard.html", context)

from accounts.models import Profile  # adapte le chemin si besoin
from .forms import ServiceOfferForm  # à créer pour ton formulaire
 # tu ajustes selon tes règles
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
import json # Nécessaire pour le parsing des tags

# Assure-toi d'importer tes modèles et fonctions utilitaires
# from .models import ServiceOffer, ServiceMedia, ServiceTag
# from .forms import ServiceOfferForm
# from .utils import can_create_new_service, get_provider_current_plan, etc.

@provider_required
def service_create_view(request):
    user = request.user
    # On récupère le profil de manière sécurisée
    profile = getattr(user, "profile", None)

    # --- 1. VÉRIFICATIONS DE SÉCURITÉ & PRÉ-REQUIS ---

    # A. Vérification KYC (Identité vérifiée)
    if profile and not profile.kyc_verified:
        messages.warning(
            request,
            "Pour publier des services, il est recommandé de faire vérifier votre identité (KYC)."
        )
        # Note: Si tu veux bloquer, change le warning en error et return redirect...

    # B. Vérification Trust Score (Score de confiance)
    # Assure-toi que MIN_TRUST_TO_PUBLISH_SERVICE est importé ou défini
    if profile and profile.trust_score < MIN_TRUST_TO_PUBLISH_SERVICE:
        messages.error(
            request,
            (
                "Votre score de confiance est trop faible pour publier un service.\n"
                "Améliorez votre comportement et obtenez de bons avis pour remonter votre score."
            )
        )
        return redirect("trust_score_dashboard")

    # C. Vérification : Prestataire validé par l'admin
    if not profile or not getattr(profile, "is_service_provider_verified", False):
        messages.error(
            request,
            "Votre compte n’a pas encore été vérifié par l’équipe. "
            "Vous pourrez publier des services dès que vous serez validé."
        )
        return redirect("profile_edit")

    # D. Vérification Limite du Plan (Services actifs)
    if not can_create_new_service(user):
        plan = get_provider_current_plan(user)
        usage = get_provider_service_usage(user)
        
        messages.error(
            request,
            f"Tu as déjà {usage['active_services']} services actifs, "
            f"ce qui est la limite de ton plan « {plan.name} ».\n"
            "Supprime ou archive un service, ou passe au plan supérieur."
        )
        return redirect("provider_dashboard")

    # --- 2. TRAITEMENT DU FORMULAIRE ---

    if request.method == "POST":
        print("recu",request.FILES)
        print("recues",request.POST)
        # On instancie le formulaire avec POST et FILES
        form = ServiceOfferForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # 1. Création de l'instance (sans sauvegarde BDD)
                service = form.save(commit=False)
                service.provider = user
                
                # 2. Vérification de l'option "Mis en avant" (Featured) par rapport au plan
                if service.is_featured and not can_set_service_featured(user):
                    plan = get_provider_current_plan(user)
                    service.is_featured = False # On désactive l'option car le plan ne le permet pas
                    messages.warning(request, f"L'option 'Mis en avant' n'est pas incluse dans votre plan « {plan.name} ».")

                # 3. Sauvegarde réelle pour obtenir l'ID
                service.save()
                
                # 4. Création des packs par défaut (Basic/Standard/Premium)
                service.create_default_packages()

                # 5. Sauvegarde des relations ManyToMany standard (Category, etc.)
                form.save_m2m()

                # ---------------------------------------------------------
                # 6. GESTION DES TAGS (via tags_input)
                # ---------------------------------------------------------
                tags_str = form.cleaned_data.get('tags_input')
                if tags_str:
                    try:
                        # Cas 1 : Format JSON (Tagify envoie souvent du JSON)
                        tag_list = json.loads(tags_str)
                        # On extrait la valeur 'value' de chaque objet tag
                        tag_names = [t['value'] for t in tag_list if 'value' in t]
                    except (json.JSONDecodeError, TypeError):
                        # Cas 2 : Format texte simple séparé par des virgules
                        tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]

                    for tag_name in tag_names:
                        # Création ou récupération du tag
                        tag, created = ServiceTag.objects.get_or_create(name=tag_name)
                        service.tags.add(tag)

                # ---------------------------------------------------------
                # 7. GESTION DES FICHIERS MÉDIAS (Images & Docs)
                # ---------------------------------------------------------
                # On utilise request.FILES directement pour être sûr de tout récupérer
                media_files = request.FILES.getlist("media_files")
                
                for f in media_files:
                    content_type = (f.content_type or "").lower()
                    
                    if content_type.startswith("image/"):
                        ServiceMedia.objects.create(
                            service=service,
                            media_type="image",
                            image=f,
                        )
                    else:
                        # On considère que c'est un document (PDF, etc.)
                        ServiceMedia.objects.create(
                            service=service,
                            media_type="document", # Assure-toi que c'est bien 'document' ou 'file' dans ton model
                            file=f,
                        )

                # ---------------------------------------------------------
                # 8. GESTION DES VIDÉOS (URLs)
                # ---------------------------------------------------------
                video_urls_raw = form.cleaned_data.get("video_urls") or ""
                for line in video_urls_raw.splitlines():
                    url = line.strip()
                    if url:
                        ServiceMedia.objects.create(
                            service=service,
                            media_type="video",
                            video_url=url,
                        )
                
                # 9. Notifications (Alertes de recherche correspondantes)
                # (On suppose que la fonction est importée)
                try:
                    notify_users_for_new_service_matching_alerts(service)
                except Exception as e:
                    print(f"Erreur notification : {e}") # On ne bloque pas la créa pour une notif ratée

                messages.success(request, "Votre service a été créé avec succès.")
                return redirect("service_detail", slug=service.slug)

            except IntegrityError:
                # En cas de doublon de titre/slug rare
                form.add_error('title', "Un service similaire existe déjà. Modifiez légèrement le titre.")
                # Important : On renvoie form pour ne pas perdre les données saisies
                return render(request, "services/service_create.html", {"form": form})
            
            except Exception as e:
                print(f"ERREUR CRÉATION SERVICE : {e}")
                messages.error(request, f"Une erreur technique est survenue : {e}")
                return render(request, "services/service_create.html", {"form": form})

        else:
            # === CAS FORMULAIRE INVALIDE ===
            print("❌ ERREURS FORMULAIRE :", form.errors) # Pour le débug serveur
            messages.error(request, "Veuillez corriger les erreurs indiquées dans le formulaire.")
            return render(request, "services/service_create.html", {
                "form": form,
            })
    else:
        # Requête GET : Formulaire vide
        form = ServiceOfferForm()

    return render(request, "services/service_create.html", {
        "form": form,
    })
    
    
    
    
    
    
    
    
    
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from accounts.decorators import client_required, not_banned_required
from .models import ServiceOffer, ServiceOrder

MAX_ACTIVE_ORDERS_PER_CLIENT = 10
MAX_ACTIVE_ORDERS_PER_CLIENT_PER_SERVICE = 3
ACTIVE_STATUSES = ["pending", "accepted", "in_progress"]

@client_required
@not_banned_required
def service_order_create_view(request, slug):
    """
    Permet à un utilisateur (client) de passer une commande sur un service.

    Anti-spam :
      - Limite globale de commandes actives par client
      - Limite de commandes actives par client ET par service
      - Option de créneau (ProviderTimeSlot)
      - Pack + extras
    """
    service = get_object_or_404(
        ServiceOffer,
        slug=slug,
        status="active",
        visibility="public",
    )

    user = request.user

    # 🔒 Bloquer les commandes pour les prestataires au trust_score trop bas
    provider_profile = getattr(service.provider, "profile", None)
    if provider_profile and provider_profile.trust_score is not None:
        if provider_profile.trust_score < MIN_TRUST_TO_PUBLISH_SERVICE:
            messages.error(
                request,
                "Ce prestataire n'est actuellement pas autorisé à proposer ses services "
                "en raison d’un score de confiance trop bas."
            )
            return redirect("service_detail", slug=slug)

    now = timezone.now()

    # Expirer les commandes dépassées pour ce service
    ServiceOrder.objects.filter(
        service=service,
        status__in=ACTIVE_STATUSES,
        due_date__lt=now,
    ).update(
        status="expired",
        status_changed_at=now,
    )

    # 🔹 Créneau envoyé par le client (optionnel : GET ?slot= ou POST slot_id)
    slot_id = request.POST.get("slot_id") or request.GET.get("slot")
    selected_slot = None
    if slot_id:
        selected_slot = ProviderTimeSlot.objects.filter(
            id=slot_id,
            provider=service.provider,
            service=service,
        ).first()

    # 🔒 Si le service ne peut avoir qu'une seule commande active à la fois
    existing_active = False
    if service.single_active_order:
        existing_active = ServiceOrder.objects.filter(
            service=service,
            status__in=ACTIVE_STATUSES,
            due_date__gte=now,
        ).exists()

    if existing_active:
        messages.error(
            request,
            "Ce service est déjà réservé par un autre client. "
            "Vous pourrez commander à nouveau quand la commande en cours sera terminée ou expirée."
        )
        return redirect("service_detail", slug=slug)

    # 🚫 Empêcher de commander son propre service
    if service.provider_id == user.id:
        messages.error(request, "Vous ne pouvez pas commander votre propre service.")
        return redirect("service_detail", slug=slug)

    # 🔒 Vérifier la disponibilité du prestataire
    code, label = get_provider_availability_status(service.provider)
    if code in ("unavailable", "unavailable_until"):
        messages.error(
            request,
            f"Ce prestataire est actuellement indisponible ({label}). "
            "Vous ne pouvez pas passer de commande pour le moment."
        )
        return redirect("service_detail", slug=slug)

    # 🔒 Anti-spam : limiter le nombre de commandes actives globales
    active_orders_global = ServiceOrder.objects.filter(
        client=user,
        status__in=ACTIVE_STATUSES,
    ).count()
    if active_orders_global >= MAX_ACTIVE_ORDERS_PER_CLIENT:
        messages.error(
            request,
            "Vous avez déjà trop de commandes actives. "
            "Terminez ou annulez certaines commandes avant d'en créer de nouvelles."
        )
        return redirect("service_list")

    # 🔒 Anti-spam : limiter les commandes actives pour CE service
    active_orders_same_service = ServiceOrder.objects.filter(
        client=user,
        service=service,
        status__in=ACTIVE_STATUSES,
    ).count()
    if active_orders_same_service >= MAX_ACTIVE_ORDERS_PER_CLIENT_PER_SERVICE:
        messages.error(
            request,
            "Vous avez déjà plusieurs commandes actives pour ce service. "
            "Merci d’attendre leur traitement avant d’en créer une nouvelle."
        )
        return redirect("service_detail", slug=slug)

    # ─────────────────────────────
    # POST : création de la commande
    # ─────────────────────────────
    if request.method == "POST":
        description_brief = (request.POST.get("description_brief") or "").strip()
        package_id = request.POST.get("package_id")
        extras_ids = request.POST.getlist("extra_ids")
        is_urgent = request.POST.get("is_urgent") == "1"


        chosen_package = None
        chosen_extras = []

        # Pack choisi
        if package_id:
            try:
                chosen_package = service.packages.get(id=package_id, is_active=True)
            except ServicePackage.DoesNotExist:
                chosen_package = None

        # Extras choisis
        if extras_ids:
            chosen_extras = list(
                service.extras.filter(id__in=extras_ids, is_active=True)
            )

        # Calcul du prix indicatif
        package_price = chosen_package.price if chosen_package else 0
        extras_total = sum(e.price for e in chosen_extras)
        computed_total = (
            package_price + extras_total
            if (package_price or extras_total)
            else None
        )
        base_total = package_price + extras_total if (package_price or extras_total) else 0

        urgent_fee = None
        total_price = None

        if is_urgent:
            # service n'accepte pas l'urgence
            if not service.allow_urgent:
                messages.error(request, "Ce service n'accepte pas les demandes urgentes.")
                return redirect("service_detail", slug=slug)
            
            # quota urgent par jour
            today = timezone.now().date()
            urgent_today = ServiceOrder.objects.filter(
                service=service,
                is_urgent=True,
                created_at__date=today,
            ).count()

            if urgent_today >= service.urgent_max_per_day:
                messages.error(
                    request,
                    "Le quota de commandes urgentes pour aujourd’hui est atteint pour ce service."
                )
                return redirect("service_detail", slug=slug)


            # 🔹 Vérifier le quota du plan
            if not can_create_urgent_order_for_service(service):
                messages.error(
                    request,
                    "Le prestataire a atteint son quota de commandes urgentes pour aujourd’hui."
                )
                return redirect("service_detail", slug=slug)

            base_for_urgent = base_total or (service.price_max or service.price_min or 0)
            urgent_fee = int(base_for_urgent * (service.urgent_extra_percent / 100))
            total_price = base_for_urgent + urgent_fee
        else:
            total_price = base_total or None

        # Prix réellement convenu (pour l’instant None)
        agreed_price = None

        # Date d’échéance (on prend le délai max du service)
        due_date = timezone.now() + timezone.timedelta(days=service.delivery_time_max_days)

        # 🔒 Si un créneau a été choisi, vérifier qu'il n'est pas complet
        if selected_slot:
            active_for_slot = ServiceOrder.objects.filter(
                service=service,
                time_slot=selected_slot,
                status__in=ACTIVE_STATUSES,
            ).count()

            if active_for_slot >= selected_slot.capacity:
                messages.error(
                    request,
                    "Ce créneau est déjà complet. Choisissez un autre créneau disponible."
                )
                return redirect("service_detail", slug=slug)

        # ✅ Création de la commande (avec ou sans créneau)
        order = ServiceOrder.objects.create(
            service=service,
            client=user,
            provider=service.provider,
            service_title_snapshot=service.title,
            provider_username_snapshot=service.provider.username,
            description_brief=description_brief[:500],
            agreed_price=agreed_price,
            currency=service.currency,
            status="pending",
            due_date=due_date,
            max_revisions=service.revisions_included,
            time_slot=selected_slot,
            is_urgent=is_urgent,
            urgent_fee=urgent_fee,
            total_price=total_price,

            # peut être None

            # 🧩 Snapshot pack + extras
            package_name=chosen_package.title if chosen_package else "",
            package_price=package_price or None,
            extras_summary=", ".join(e.name for e in chosen_extras) if chosen_extras else "",
            extras_total_price=extras_total or None,
            computed_total_price=computed_total,
        )

        notify_service_provider_new_order(order)
        
        if order.is_urgent:
            notify_service_provider_new_urgent_order(order)

        messages.success(
            request,
            "Votre commande a été créée. Le prestataire sera notifié."
        )
        return redirect("service_order_detail", order_id=order.id)

    # ─────────────────────────────
    # GET → page de confirmation simple
    # ─────────────────────────────
    # (tu peux ajouter la liste des créneaux si ton template l’utilise)
    
    # ─────────────────────────────
# GET → affichage des créneaux avec disponibilité
# ─────────────────────────────
    from django.db.models import Count
    
    provider_time_slots = ProviderTimeSlot.objects.filter(
    provider=service.provider,
    # service=service,
    ).order_by("weekday", "start_time")

# Compter les commandes actives par créneau
    active_counts = ServiceOrder.objects.filter(
    service=service,
    status__in=ACTIVE_STATUSES,
    ).values("time_slot").annotate(total=Count("id"))

# Transformer en dictionnaire {slot_id: total}
    active_dict = {item["time_slot"]: item["total"] for item in active_counts}

    slots_with_availability = []

    for slot in provider_time_slots:
        active_for_slot = active_dict.get(slot.id, 0)
        remaining = slot.capacity - active_for_slot

        slots_with_availability.append({
        "slot": slot,
        "remaining": remaining,
        "is_full": remaining <= 0
        })

    return render(request, "services/service_order_confirm.html", {
    "service": service,
    "slots_with_availability": slots_with_availability,
    "selected_slot": selected_slot,
})
                         
@login_required
def service_order_detail_view(request, order_id):
    """
    Détail d’une commande.
    Seul le client ou le prestataire peuvent y accéder.
    """
    order = get_object_or_404(
        ServiceOrder.objects.select_related("service", "client", "provider"),
        id=order_id,
    )

    if not order.can_user_view(request.user):
        messages.error(request, "Vous n'avez pas accès à cette commande.")
        return redirect("service_list")

    context = {
        "order": order,
    }
    return render(request, "services/service_order_detail.html", context)


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from accounts.decorators import provider_required
from .models import ServiceOrder
from .forms import ServiceOrderStatusForm


@provider_required
def service_order_change_status_view(request, order_id):
    """
    Permet au PRESTATAIRE de changer le statut d'une commande.
    - Seul le provider de la commande peut y accéder
    - Les transitions sont contrôlées par ServiceOrder.change_status()
    """
    order = get_object_or_404(
        ServiceOrder.objects.select_related("service", "client", "provider"),
        id=order_id,
    )

    # 🔐 Sécurité : seul le prestataire peut gérer cette commande
    if not order.is_provider(request.user):
        messages.error(request, "Vous n'êtes pas le prestataire de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        form = ServiceOrderStatusForm(request.POST, order=order)
        if form.is_valid():
            new_status = form.cleaned_data["new_status"]
            reason = form.cleaned_data["reason"] or ""

            try:
                # 🔥 Utilise la méthode robuste du modèle (transitions + historique)
                order.change_status(new_status, actor=request.user, reason=reason)
                messages.success(request, f"Le statut de la commande est passé à « {order.get_status_display()} ».")
            except ValueError as e:
                # Par exemple si quelqu'un bricole le POST
                messages.error(request, f"Changement de statut invalide : {e}")

            return redirect("service_order_detail", order_id=order.id)
    else:
        form = ServiceOrderStatusForm(order=order)

        if not form.fields["new_status"].choices:
            messages.info(
                request,
                "Aucun changement de statut n'est possible pour cette commande (elle est probablement terminée ou annulée)."
            )
            return redirect("service_order_detail", order_id=order.id)

    return render(request, "services/service_order_change_status.html", {
        "order": order,
        "form": form,
    })
    
    
@login_required
def service_order_detail_view(request, order_id):
    """
    Détail d’une commande.
    Seul le client ou le prestataire peuvent y accéder.
    """
    order = get_object_or_404(
        ServiceOrder.objects.select_related("service", "client", "provider"),
        id=order_id,
    )

    if not order.can_user_view(request.user):
        messages.error(request, "Vous n'avez pas accès à cette commande.")
        return redirect("service_list")

    context = {
        "order": order,
    }
    return render(request, "services/service_order_detail.html", context)


from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import client_required, not_banned_required
from .models import ServiceOrder
from .forms import ServiceOrderClientActionForm


@client_required
@not_banned_required
@require_http_methods(["GET", "POST"])
def service_order_client_action_view(request, order_id):
    """
    Permet au CLIENT d'une commande de :
      - confirmer que le service est terminé (completed)
      - demander l'annulation (cancelled)
    en fonction du statut actuel de la commande.
    """
    order = get_object_or_404(
        ServiceOrder.objects.select_related("service", "client", "provider"),
        id=order_id,
    )

    # 🔐 Sécurité : seul le CLIENT de la commande peut utiliser cette vue
    if not order.is_client(request.user):
        messages.error(request, "Vous n'êtes pas le client de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        form = ServiceOrderClientActionForm(request.POST, order=order)
        if form.is_valid():
            try:
                form.apply(actor=request.user)
                messages.success(
                    request,
                    f"L'action a bien été prise en compte. Nouveau statut : {order.get_status_display()}."
                )
            except ValueError as e:
                # Erreur de transition invalide (au cas où)
                messages.error(request, f"Impossible de changer le statut : {e}")
            return redirect("service_order_detail", order_id=order.id)
    else:
        form = ServiceOrderClientActionForm(order=order)

        if not form.fields["action"].choices:
            messages.info(
                request,
                "Aucune action n'est possible pour cette commande (elle est peut-être déjà terminée ou annulée)."
            )
            return redirect("service_order_detail", order_id=order.id)

    return render(request, "services/service_order_client_action.html", {
        "order": order,
        "form": form,
    })
    
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import ServiceSearchAlert


@login_required
def service_search_alert_list_view(request):
    alerts = ServiceSearchAlert.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "services/service_search_alert_list.html", {
        "alerts": alerts,
    })


@login_required
def service_search_alert_toggle_active_view(request, alert_id):
    alert = get_object_or_404(ServiceSearchAlert, id=alert_id, user=request.user)
    alert.is_active = not alert.is_active
    alert.save(update_fields=["is_active"])

    if alert.is_active:
        messages.success(request, "Cette alerte est maintenant active. Vous recevrez des notifications.")
    else:
        messages.info(request, "Cette alerte a été désactivée. Vous ne recevrez plus de notifications pour cette recherche.")

    return redirect("service_search_alert_list")


@login_required
def service_search_alert_delete_view(request, alert_id):
    alert = get_object_or_404(ServiceSearchAlert, id=alert_id, user=request.user)
    alert.delete()
    messages.success(request, "Votre alerte de recherche a été supprimée.")
    return redirect("service_search_alert_list")


from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import provider_required
from .models import ServiceOffer
from .forms import ServiceOfferForm


@provider_required
def service_edit_view(request, slug):
    """
    Modification d'un service existant par son prestataire.
    """
    service = get_object_or_404(ServiceOffer, slug=slug)

    # 🔐 sécurité : seul le prestataire peut éditer
    if service.provider != request.user:
        messages.error(request, "Vous n'êtes pas le prestataire de ce service.")
        return redirect("service_detail", slug=service.slug)

    if request.method == "POST":
        form = ServiceOfferForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            service_obj = form.save(commit=False)

            if service_obj.is_featured and not can_set_service_featured(request.user):
                plan = get_provider_current_plan(request.user)
                messages.error(request,f"Tu as atteint la limite de services mis en avant pour ton plan « {plan.name} ».")
        service_obj.is_featured = False
        service_obj.save()
        messages.success(request, "Service mis à jour.")
        form.save_m2m()
            # 🔹 Ajouter de nouveaux fichiers (on ne supprime pas les anciens ici)
        media_files = request.FILES.getlist("media_files")
        for f in media_files:
            
            content_type = (f.content_type or "").lower()
            if content_type.startswith("image/"):
                ServiceMedia.objects.create(
                service=service,
                media_type="image",
                image=f,
                )
            else:
                ServiceMedia.objects.create(
                service=service,
                media_type="file",
                file=f,
                )

            # 🔹 Vidéos supplémentaires
            video_urls_raw = form.cleaned_data.get("video_urls") or ""
            for line in video_urls_raw.splitlines():
                url = line.strip()
                if not url:
                    continue
                ServiceMedia.objects.create(
                    service=service,
                    media_type="video",
                    video_url=url,
                )
            # provider déjà défini, pas besoin de le repasser
            messages.success(request, "Votre service a été mis à jour.")
            return redirect("service_detail", slug=service.slug)
    else:
        form = ServiceOfferForm(instance=service)

    return render(request, "services/service_edit.html", {
        "form": form,
        "service": service,
    })
    
    
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from accounts.decorators import provider_required, not_banned_required
from .models import ServiceOrder
from stages.models import Conversation,Message
# si tu as une fonction de notif client, tu pourras l'importer ici :
# from .utils_notifications import notify_client_order_status_change


@provider_required
@not_banned_required
def service_order_accept_view(request, order_id):
    """
    Vue pour que le PRESTATAIRE accepte une commande.
    - Accessible uniquement si l'utilisateur est le provider de la commande
    - Et que la commande est encore en statut 'pending'
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    # Vérifier que c'est bien le prestataire
    if order.provider != request.user:
        messages.error(request, "Vous n'êtes pas le prestataire de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    # Vérifier le statut
    if order.status != "pending":
        messages.warning(request, "Cette commande n'est plus en attente, vous ne pouvez pas l'accepter.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        order.status = "accepted"
        order.status_changed_at = timezone.now()
        order.save(update_fields=["status", "status_changed_at"])

        # Notifier le client (si tu as déjà une fonction pour ça)
        notify_client_order_status_change(order, old_status="pending", new_status="accepted")
        # 💬 créer la conversation si elle n'existe pas déjà
        if not hasattr(order, "conversation") or order.conversation is None:
            convo = Conversation.objects.create(
                service_order=order,
                # on mappe client ↔ student, provider ↔ company
                student=order.client,
                company=order.provider,
                is_active=True,
            )

            Message.objects.create(
                conversation=convo,
                sender=request.user,
                text=(
                    "Bonjour, j'ai accepté votre commande pour ce service. "
                    "Nous pouvons discuter ici des détails et du prix."
                ),
                msg_type="systeme",
            )
        

        messages.success(request, "Commande acceptée. Une discussion a été ouverte avec le client.")
        return redirect("service_order_detail", order_id=order.id)

    # En GET, tu peux soit rediriger direct, soit afficher une page de confirmation
    return redirect("service_order_detail", order_id=order.id)


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import ServiceOffer, FavoriteService

@login_required
def service_toggle_favorite_view(request, service_id):
    """
    Ajoute ou retire un service des favoris de l'utilisateur.
    """
    # On autorise les favoris uniquement pour des services visibles
    service = get_object_or_404(
        ServiceOffer,
        id=service_id,
        status="active",
        visibility="public",
    )

    fav, created = FavoriteService.objects.get_or_create(
        user=request.user,
        service=service,
    )

    if created:
        messages.success(request, "Service ajouté à vos favoris.")
    else:
        fav.delete()
        messages.info(request, "Service retiré de vos favoris.")

    # On essaie de revenir sur la page précédente
    next_url = request.META.get("HTTP_REFERER") or redirect("service_list").url
    return redirect(next_url)
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from accounts.decorators import provider_required, client_required, not_banned_required
from .models import ServiceOrder
# from .utils_notifications import notify_client_order_status_change  # si tu l’as


@provider_required
@not_banned_required
def service_order_reject_view(request, order_id):
    """
    Le PRESTATAIRE refuse une commande.
    Autorisé seulement si la commande est encore 'pending'.
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    # vérifier que c’est bien le prestataire
    if order.provider != request.user:
        messages.error(request, "Vous n'êtes pas le prestataire de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    if order.status != "pending":
        messages.warning(request, "Cette commande n'est plus en attente, vous ne pouvez plus la refuser.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        old_status = order.status
        order.status = "cancelled"
        order.status_changed_at = timezone.now()
        order.save(update_fields=["status", "status_changed_at"])
        #penalite sur le score
        decrease_trust_score(order.provider, 15, "Annulation par le prestataire")


        # Notifier le client si besoin
        notify_client_order_status_change(order, old_status, "cancelled")

        messages.success(request, "Vous avez refusé cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    return redirect("service_order_detail", order_id=order.id)

        


@client_required
@not_banned_required
def service_order_cancel_view(request, order_id):
    """
    Le CLIENT annule sa commande.
    Autorisé tant que la commande n’est pas terminée ou déjà annulée.
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    if order.client != request.user:
        messages.error(request, "Vous n'êtes pas le client de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    # tu peux décider exactement quand l’annulation est possible
    if order.status not in ["pending", "accepted", "in_progress"]:
        messages.warning(request, "Cette commande ne peut plus être annulée.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        old_status = order.status
        order.status = "cancelled"
        order.status_changed_at = timezone.now()
        order.save(update_fields=["status", "status_changed_at"])

        # notifier le prestataire si tu veux
        
        notify_provider_order_status_change(order, old_status, "canceled")


        messages.success(request, "Vous avez annulé cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    return redirect("service_order_detail", order_id=order.id)




@provider_required
@not_banned_required
def service_order_mark_complete_provider_view(request, order_id):
    """
    Le PRESTATAIRE clique sur 'Terminer la commande'.
    On ne passe en 'completed' que si le client a aussi confirmé.
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    if order.provider != request.user:
        messages.error(request, "Vous n'êtes pas le prestataire de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    if order.status not in ["accepted", "in_progress"]:
        messages.warning(request, "Cette commande ne peut pas être marquée comme terminée à ce stade.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        old_status = order.status
        order.provider_mark_complete = True

        # Si le client a aussi confirmé → on finalise
        if order.client_mark_complete and order.status != "completed":
            old_status = order.status
            order.status = "completed"
            order.status_changed_at = timezone.now()
            order.save(update_fields=[
                "provider_mark_complete",
                "status",
                "status_changed_at",
            ])
            messages.success(request, "Commande terminée (vous et le client avez confirmé).")
        else:
            order.save(update_fields=["provider_mark_complete"])
            messages.info(
                request,
                "Vous avez marqué la commande comme terminée. "
                "Elle sera finalisée dès que le client confirmera aussi."
            )
            notify_client_order_status_change(order, old_status, "completed")
            notify_provider_order_status_change(order, old_status, "completed")

        return redirect("service_order_detail", order_id=order.id)

    return redirect("service_order_detail", order_id=order.id)

@client_required
@not_banned_required
def service_order_mark_complete_client_view(request, order_id):
    """
    Le CLIENT clique sur 'Terminer la commande'.
    On ne passe en 'completed' que si le prestataire a aussi confirmé.
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    if order.client != request.user:
        messages.error(request, "Vous n'êtes pas le client de cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    if order.status not in ["accepted", "in_progress"]:
        messages.warning(request, "Cette commande ne peut pas être marquée comme terminée à ce stade.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        old_status = order.status
        order.client_mark_complete = True

        if order.provider_mark_complete and order.status != "completed":
            old_status = order.status
            order.status = "completed"
            order.status_changed_at = timezone.now()
            order.save(update_fields=[
                "client_mark_complete",
                "status",
                "status_changed_at",
            ])
            messages.success(request, "Commande terminée (vous et le prestataire avez confirmé).")
        else:
            order.save(update_fields=["client_mark_complete"])
            
            messages.info(
                request,
                "Vous avez marqué la commande comme terminée. "
                "Elle sera finalisée dès que le prestataire confirmera aussi."
            )
        notify_client_order_status_change(order, old_status, "completed")
        notify_provider_order_status_change(order, old_status, "completed")


        return redirect("service_order_detail", order_id=order.id)

    return redirect("service_order_detail", order_id=order.id)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import FavoriteService, ServiceOffer
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import FavoriteService


@login_required
def my_favorite_services_view(request):
    """
    Liste des services favoris de l'utilisateur avec tri.
    sort peut être :
      - recent (par défaut)
      - price_asc
      - price_desc
      - rating_desc
      - rating_asc
      - title
    """
    user = request.user
    sort = request.GET.get("sort", "recent")

    fav_links = (
        FavoriteService.objects
        .filter(user=user)
        .select_related("service", "service__provider")
    )

    # Tri
    if sort == "price_asc":
        fav_links = fav_links.order_by("service__price_min")
    elif sort == "price_desc":
        fav_links = fav_links.order_by("-service__price_min")
    elif sort == "rating_desc":
        fav_links = fav_links.order_by("-service__average_rating")
    elif sort == "rating_asc":
        fav_links = fav_links.order_by("service__average_rating")
    elif sort == "title":
        fav_links = fav_links.order_by("service__title")
    else:  # recent (par défaut)
        fav_links = fav_links.order_by("-created_at")

    context = {
        "favorite_links": fav_links,
        "sort": sort,
    }
    return render(request, "services/my_favorite_services.html", context)



from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from .models import ServiceOrder, ServiceReview
from .forms import ServiceReviewForm
from accounts.decorators import client_required, not_banned_required


from .utils_scores import decrease_trust_score, increase_trust_score
    
@login_required
@client_required
@not_banned_required
def service_review_create_view(request, order_id):
    """
    Permet au client de laisser une note + avis sur un service,
    UNIQUEMENT si la commande est terminée, pas encore notée
    et que le client n'a pas trop de signalements ouverts.
    """
    order = get_object_or_404(
        ServiceOrder,
        id=order_id,
        client=request.user
    )
    
    # 1) Commande doit être terminée
    if order.status != "completed":
        messages.error(request, "Vous ne pouvez noter ce service que lorsque la commande est terminée.")
        return redirect("service_order_detail", order_id=order.id)

    # 2) Un avis existe déjà ?
    if hasattr(order, "review"):
        messages.info(request, "Vous avez déjà laissé un avis pour cette commande.")
        return redirect("service_order_detail", order_id=order.id)

    # 3) Trop de signalements ouverts contre ce client ?
    open_reports_against_client = ServiceOrderReport.objects.filter(
        reported=request.user,
        status__in=["open", "in_review"],
    ).count()

    if open_reports_against_client >= MAX_OPEN_REPORTS_FOR_REVIEW:
        messages.error(
            request,
            "Vous ne pouvez pas laisser d'avis pour le moment car votre compte a plusieurs "
            "signalements en cours. Veuillez contacter le support."
        )
        return redirect("service_order_detail", order_id=order.id)

    # 4) Optionnel : signalement spécifique sur CETTE commande
    order_reports_against_client = ServiceOrderReport.objects.filter(
        order=order,
        reported=request.user,
        status__in=["open", "in_review"],
    ).exists()

    if order_reports_against_client:
        messages.error(
            request,
            "Un signalement est en cours sur cette commande. Vous ne pouvez pas laisser d'avis "
            "tant que le problème n'est pas résolu."
        )
        return redirect("service_order_detail", order_id=order.id)

    # 5) Ok, on affiche / traite le formulaire d'avis
    if request.method == "POST":
        form = ServiceReviewForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data.get("rating")
            comment = form.cleaned_data.get("comment", "") or ""

            # 1) Spam check (max 5 bad reviews per day by this client)
            today = timezone.now().date()
            bad_reviews_today = ServiceReview.objects.filter(
                client=request.user,
                rating__lte=2,
                created_at__date=today,
            ).count()

            if bad_reviews_today >= 5:
                messages.error(
                    request,
                    "Tu as déjà laissé plusieurs avis très négatifs aujourd'hui. "
                    "Merci d'utiliser le système de manière responsable."
                )
                return redirect("service_order_detail", order_id=order.id)

            # 2) Mandatory comment for low scores
            if rating <= 2 and not comment.strip():
                messages.error(
                    request,
                    "Pour les notes basses, merci d'expliquer en quelques mots ce qui n'a pas été."
                )
                return redirect("service_order_detail", order_id=order.id)

            # 3) Process and Save Review
            review = form.save(commit=False)
            review.order = order
            review.service = order.service
            review.client = request.user
            review.save()
            
            # 🔻 Logic for trust_score (impacts the provider)
            if rating <= 1:
                decrease_trust_score(order.provider, 20, "Avis client 1/5")
            elif rating == 2:
                decrease_trust_score(order.provider, 10, "Avis client 2/5")
            elif rating >= 4:
                increase_trust_score(order.provider, 5, f"Avis positif {rating}/5")

            messages.success(request, "Merci pour votre avis !")
            return redirect("service_order_detail", order_id=order.id)
    else:
        form = ServiceReviewForm()

    return render(request, "services/service_review_form.html", {
        "order": order,
        "service": order.service,
        "form": form,
    })
    

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from .models import ServiceOrder, ServiceReview
from .forms import ServiceReviewForm  # si tu as un formulaire


@login_required
@not_banned_required
def service_order_report_view(request, order_id):
    """
    Permet de signaler un problème sur une commande (client ou prestataire).
    - Le client peut signaler le prestataire
    - Le prestataire peut signaler le client
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    user = request.user

    if user != order.client and user != order.provider:
        messages.error(request, "Vous ne pouvez signaler que vos propres commandes.")
        return redirect("home")

    # Déterminer qui est la personne signalée
    if user == order.client:
        reported_user = order.provider
    else:
        reported_user = order.client

    # Vérifier si ce user a déjà fait un signalement pour cette commande
    existing_report = ServiceOrderReport.objects.filter(
        order=order,
        reporter=user,
    ).first()

    if existing_report:
        messages.info(request, "Vous avez déjà signalé cette commande. Merci d'attendre le traitement.")
        return redirect("service_order_detail", order_id=order.id)

    if request.method == "POST":
        form = ServiceOrderReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.order = order
            report.reporter = user
            report.reported = reported_user
            report.status = "open"
            report.save()
            
            decrease_trust_score(order.provider, 15, "Signalement(abus/comportement)")

            messages.success(
                request,
                "Votre signalement a été enregistré. L'équipe de modération l'examinera."
            )
            return redirect("service_order_detail", order_id=order.id)
    else:
        form = ServiceOrderReportForm()

    return render(request, "services/service_order_report_form.html", {
        "order": order,
        "reported_user": reported_user,
        "form": form,
    })
    
@login_required
def service_order_invoice_view(request, order_id):
    """
    Génère un PDF 'preuve de prestation / reçu de commande' pour un ServiceOrder.
    Accessible uniquement au client, au prestataire ou au staff.
    """
    order = get_object_or_404(ServiceOrder, id=order_id)

    # Sécurité : qui a le droit ?
    if request.user not in (order.client, order.provider) and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas accès à ce reçu.")
        return redirect("home")

    if render_html_to_pdf_bytes is None:
        messages.error(
            request,
            "La génération de PDF n'est pas encore configurée. "
            "Vérifiez votre utils_pdf dans l'app stages."
        )
        return redirect("service_order_detail", order_id=order.id)

    context = {
        "order": order,
        "service": order.service,
        "client": order.client,
        "provider": order.provider,
    }

    pdf_bytes = render_html_to_pdf_bytes("services/service_order_invoice.html", context)
    if not pdf_bytes:
        messages.error(request, "Impossible de générer le PDF pour le moment.")
        return redirect("service_order_detail", order_id=order.id)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    # inline = affichage dans le navigateur ; attachment = téléchargement direct
    filename = f"prestation_service_{order.id}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


# accounts/views.py


from .models import ServicePackage
from .forms import ServicePackageForm
from django.http import Http404

@provider_required
def service_package_edit_view(request, pk):
    """
    Modifie un pack d’un service.
    Accessible uniquement par le prestataire propriétaire du service.
    L’édition se fait via le modal → POST uniquement.
    """
    package = get_object_or_404(
        ServicePackage,
        pk=pk,
        service__provider=request.user  # sécurité
    )

    if request.method != "POST":
        raise Http404("Édition de pack uniquement via le modal.")

    # Récupération des champs envoyés par le modal
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()
    price_raw = (request.POST.get("price") or "").strip()
    days_raw = (request.POST.get("delivery_time_days") or "").strip()

    errors = []

    if not title:
        errors.append("Le nom du pack est requis.")

    try:
        price = int(price_raw)
        if price < 0:
            errors.append("Le prix doit être positif.")
    except ValueError:
        errors.append("Le prix est invalide.")

    try:
        delivery_time_days = int(days_raw)
        if delivery_time_days < 1:
            errors.append("Le délai doit être au moins 1 jour.")
    except ValueError:
        errors.append("Le délai est invalide.")

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect("service_detail", slug=package.service.slug)

    # ✅ Mise à jour réelle
    package.title = title
    package.description = description
    package.price = price
    package.delivery_time_days = delivery_time_days
    package.save()

    messages.success(request, "Pack mis à jour avec succès.")
    return redirect("service_detail", slug=package.service.slug)
@provider_required
def service_package_create_view(request, slug):
    """
    Crée un nouveau pack pour un service appartenant au prestataire connecté.
    """
    service = get_object_or_404(
        ServiceOffer,
        slug=slug,
        provider=request.user,  # sécurité : seul le propriétaire peut créer des packs
    )

    if request.method != "POST":
        # On ne sert pas de formulaire standalone (tout se fait via le modal)
        raise Http404("Création de pack uniquement via le modal.")

    form = ServicePackageForm(request.POST)
    if form.is_valid():
        package = form.save(commit=False)
        package.service = service

        # 🔹 Assigner un code automatiquement (basic → standard → premium)
        existing_codes = set(service.packages.values_list("code", flat=True))
        if "basic" not in existing_codes:
            package.code = "basic"
        elif "standard" not in existing_codes:
            package.code = "standard"
        else:
            package.code = "premium"

        package.is_active = True
        package.save()

        messages.success(request, "Nouveau pack créé avec succès.")
    else:
        # 🔍 Pour debug dans le terminal
        print("ERREURS ServicePackageForm (create) :", form.errors)

        # 🔔 Message plus clair dans l'interface
        messages.error(
            request,
            "Certains champs du pack sont invalides : "
            f"{form.errors.as_text()}"
        )

    return redirect("service_detail", slug=service.slug)
@provider_required
def service_package_delete_view(request, pk):
    """
    Supprime un pack appartenant au prestataire connecté.
    Suppression uniquement en POST.
    """
    package = get_object_or_404(
        ServicePackage.objects.select_related("service", "service__provider"),
        pk=pk,
        service__provider=request.user,  # sécurité : seulement le propriétaire
    )

    if request.method != "POST":
        package_title = package.title
        
        raise Http404("Suppression de pack uniquement en POST.")

    service_slug = package.service.slug
    package_name = package.title

    package.delete()
    messages.success(
        request,
        f"Le pack « {package_name} » a été supprimé."
    )
    return redirect("service_detail", slug=service_slug)




@provider_required
@not_banned_required
def service_delete_view(request, slug):
    """
    Permet à un prestataire de supprimer ou désactiver son propre service.

    - Si aucune commande n'existe → suppression définitive.
    - Si des commandes existent → on le passe en 'archived' + 'hidden'
      et on prévient les clients par email.
    """
    service = get_object_or_404(
        ServiceOffer,
        slug=slug,
        provider=request.user,  # sécurité : seul le propriétaire
    )

    if request.method != "POST":
        messages.error(request, "Suppression de service uniquement en POST.")
        return redirect("service_detail", slug=service.slug)

    # Est-ce qu'il y a déjà des commandes pour ce service ?
    has_orders = ServiceOrder.objects.filter(service=service).exists()

    if not has_orders:
        # 🔥 Pas de commandes → suppression définitive
        title = service.title
        service.delete()
        messages.success(
            request,
            f"Le service « {title} » a été supprimé définitivement."
        )
    else:
        # 🧊 Il y a des commandes → désactivation + email aux clients
        service.status = "archived"    # adapte à tes choices si besoin
        service.visibility = "hidden"  # idem
        service.save(update_fields=["status", "visibility"])

        # Récupérer les clients qui ont déjà commandé ce service
        client_ids = (
            ServiceOrder.objects
            .filter(service=service)
            .values_list("client_id", flat=True)
            .distinct()
        )
        User = get_user_model()
        clients = User.objects.filter(id__in=client_ids)

        notify_clients_service_deactivated(service, clients)

        messages.info(
            request,
            "Ce service avait déjà des commandes. Il a été désactivé et les clients concernés "
            "ont été prévenus par email."
        )

    return redirect("provider_dashboard")



# services/views.py

from django.shortcuts import render, redirect
from .models import ProviderTimeSlot
from .forms import ProviderTimeSlotForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
# Assurez-vous d'importer votre décorateur personnalisé s'il existe
# from .decorators import provider_required 
from .models import ProviderTimeSlot

# @provider_required (Activez ceci si vous utilisez votre décorateur personnalisé)
@login_required
@require_POST
def delete_slot(request, slot_id):
    # On récupère le slot, mais on s'assure qu'il appartient bien à l'utilisateur connecté (provider)
    # C'est une sécurité cruciale pour qu'un provider ne supprime pas le créneau d'un autre.
    slot = get_object_or_404(ProviderTimeSlot, id=slot_id, provider=request.user)
    
    # Suppression
    slot.delete()
    
    # Message de confirmation
    messages.success(request, "Le créneau de disponibilité a été supprimé.")
    
    # Redirection vers la liste
    return redirect("provider_timeslots")
@provider_required
def provider_timeslots_view(request):
    provider = request.user
    if not can_create_new_slot(provider):
        plan = get_provider_current_plan(provider)
        used = get_provider_slot_usage(provider)

        messages.error(
            request,
            f"Tu as déjà créé {used} créneaux, ce qui correspond à la limite "
            f"de ton plan « {plan.name} » ({plan.max_time_slots} créneaux max)."
        )
        return redirect("provider_timeslots")

    if request.method == "POST":
        form = ProviderTimeSlotForm(request.POST)
        if form.is_valid():
            ts = form.save(commit=False)
            ts.provider = provider
            ts.save()
            messages.success(request, "Créneau ajouté avec succès.")
            return redirect("provider_timeslots")
    else:
        form = ProviderTimeSlotForm()

    # Les créneaux déjà créés
    slots = ProviderTimeSlot.objects.filter(provider=provider)

    return render(request, "services/provider_timeslots.html", {
        "form": form,
        "slots": slots,
    })
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ProviderTimeSlot
from .forms import ProviderTimeSlotForm

# ... votre vue existante provider_timeslots_view ...

@login_required
def provider_timeslot_edit(request, pk):
    """
    Vue pour modifier un créneau existant.
    """
    timeslot = get_object_or_404(ProviderTimeSlot, pk=pk, provider=request.user)

    if request.method == 'POST':
        form = ProviderTimeSlotForm(request.POST, instance=timeslot)
        if form.is_valid():
            form.save()
            messages.success(request, "Créneau modifié avec succès.")
            return redirect('provider_timeslots')
        else:
            messages.error(request, "Erreur lors de la modification. Vérifiez les horaires.")
    
    return redirect('provider_timeslots')

@login_required
@require_POST
def provider_timeslot_delete(request, pk):
    """
    Vue pour supprimer un créneau.
    """
    timeslot = get_object_or_404(ProviderTimeSlot, pk=pk, provider=request.user)
    timeslot.delete()
    messages.success(request, "Créneau supprimé du planning.")
    return redirect('provider_timeslots')
    
from accounts.models import SubscriptionPlan, Subscription
from .utils_subscriptions import get_provider_current_plan, send_subscription_changed_email

@login_required
def subscription_upgrade_view(request):
    current_plan = get_provider_current_plan(request.user)
    plans = SubscriptionPlan.objects.filter(role_target='provider', is_active=True).order_by("price")

    return render(request, "services/subscription_upgrade.html", {
        "current_plan": current_plan,
        "plans": plans,
    })
    
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import provider_required

@provider_required
def subscription_upgrade_confirm_view(request, plan_code):
    user = request.user
    old_plan = get_provider_current_plan(user)

    target_plan = get_object_or_404(
        SubscriptionPlan,
        code=plan_code,
        role_target='provider',
        is_active=True,
    )

    if target_plan.code == old_plan.code:
        messages.info(request, "Tu es déjà sur ce plan.")
        return redirect("subscription_upgrade")

    if request.method == "POST":
        if target_plan.price > 0:
            from django.urls import reverse
            return redirect(f"{reverse('payments:initiate_payment')}?plan_id={target_plan.id}&amount={target_plan.price}")

        now = timezone.now()
        # Désactiver l'ancien abonnement
        Subscription.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)

        # Créer le nouvel abonnement gratuit
        new_sub = Subscription.objects.create(
            user=user,
            plan=target_plan,
            start_date=now,
            end_date=now + timedelta(days=365),
            is_active=True,
            is_trial=False
        )

        # ✉️ envoi de l'email de confirmation
        try:
            send_subscription_changed_email(
                provider=user,
                old_plan=old_plan,
                new_plan=target_plan,
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            pass

        messages.success(
            request,
            f"Ton abonnement a été mis à jour vers le plan « {target_plan.name} »."
        )
        return redirect("provider_dashboard")

    return render(request, "services/subscription_upgrade_confirm.html", {
        "current_plan": old_plan,
        "target_plan": target_plan,
    })
    
    
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from django.contrib.auth import get_user_model
from .models import ProviderFollow

User = get_user_model()

@login_required
def service_toggle_follow_view(request, provider_id):
    """
    Permet à un utilisateur de s'abonner ou se désabonner d'un prestataire.
    """
    provider = get_object_or_404(User, id=provider_id)
    print("jhgkhlljljljlkj",provider_id)

    # impossible de se suivre soi-même
    if provider == request.user:
        messages.error(request, "Tu ne peux pas t'abonner à toi-même.")
        return redirect(request.META.get("HTTP_REFERER", "service_list"))

    # on vérifie qu'il est bien prestataire
    profile = getattr(provider, "profile", None)
    if not profile or not profile.is_service_provider:
        messages.error(request, "Cet utilisateur n'est pas un prestataire de services.")
        return redirect(request.META.get("HTTP_REFERER", "service_list"))

    follow, created = ProviderFollow.objects.get_or_create(
        client=request.user,
        provider=provider,
    )

    if created:
        messages.success(request, f"Tu es maintenant abonné(e) à {provider.username}.")
    else:
        follow.delete()
        messages.info(request, f"Tu t'es désabonné(e) de {provider.username}.")

    return redirect(request.META.get("HTTP_REFERER", "service_list"))


# services/views.py

from django.utils import timezone
from django.db.models import (
    Q, Sum, Count, Case, When, BooleanField, F
)
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from accounts.decorators import provider_required
from .models import ServiceOrder, ServiceOffer

# Adapte si tu as déjà ça ailleurs
ACTIVE_STATUSES = ["pending", "accepted", "in_progress"]
DONE_STATUSES = ["completed"]
CANCELLED_STATUSES = ["cancelled", "refused", "expired"]  # adapte à tes choix


@provider_required
def provider_orders_list_view(request):
    """
    Dashboard des commandes d'un prestataire :
    - filtre par statut
    - recherche (service, client, id)
    - filtre urgentes
    - filtre plage de dates
    - pagination
    - stats rapides en haut
    """
    user = request.user

    # --------- filtres GET ----------
    status_filter = (request.GET.get("status") or "").strip()  # all / active / done / cancelled / pending / ...
    urgent_only   = (request.GET.get("urgent") == "1")
    q             = (request.GET.get("q") or "").strip()
    date_from_raw = (request.GET.get("from") or "").strip()
    date_to_raw   = (request.GET.get("to") or "").strip()
    service_id    = (request.GET.get("service") or "").strip()

    # --------- base queryset : commandes de MES services ----------
    orders = (
        ServiceOrder.objects
        .filter(provider=user)
        .select_related("service", "client", "client__profile")
        .order_by("-created_at")
    )

    # --------- filtre statut "macro" ----------
    if status_filter == "active":
        orders = orders.filter(status__in=ACTIVE_STATUSES)
    elif status_filter == "done":
        orders = orders.filter(status__in=DONE_STATUSES)
    elif status_filter == "cancelled":
        orders = orders.filter(status__in=CANCELLED_STATUSES)
    elif status_filter in (ACTIVE_STATUSES + DONE_STATUSES + CANCELLED_STATUSES):
        # filtre direct sur un statut unique, ex: ?status=pending
        orders = orders.filter(status=status_filter)
    # sinon status_filter vide → pas de filtre

    # --------- filtre urgentes ----------
    if urgent_only:
        # adapte le nom de champ si ce n’est pas is_urgent
        orders = orders.filter(is_urgent=True)

    # --------- filtre par service ----------
    if service_id.isdigit():
        orders = orders.filter(service_id=int(service_id))

    # --------- filtre texte ----------
    if q:
        orders = orders.filter(
            Q(service__title__icontains=q)
            | Q(client__username__icontains=q)
            | Q(client__email__icontains=q)
            | Q(id__icontains=q)
        )

    # --------- filtre dates ----------
    # On prend created_at entre from et to
    if date_from_raw:
        try:
            # format "YYYY-MM-DD" depuis un input type="date"
            date_from = timezone.datetime.fromisoformat(date_from_raw).date()
            orders = orders.filter(created_at__date__gte=date_from)
        except ValueError:
            date_from = None
    else:
        date_from = None

    if date_to_raw:
        try:
            date_to = timezone.datetime.fromisoformat(date_to_raw).date()
            orders = orders.filter(created_at__date__lte=date_to)
        except ValueError:
            date_to = None
    else:
        date_to = None

    # --------- annotation : est en retard ? ----------
    now = timezone.now()
    orders = orders.annotate(
        is_late=Case(
            When(
                Q(status__in=ACTIVE_STATUSES) & Q(due_date__lt=now),
                then=True,
            ),
            default=False,
            output_field=BooleanField(),
        )
    )

    # --------- stats globales (avant pagination) ----------
    base_qs = ServiceOrder.objects.filter(provider=user)

    # total en cours
    total_active = base_qs.filter(status__in=ACTIVE_STATUSES).count()
    # total terminées
    total_done = base_qs.filter(status__in=DONE_STATUSES).count()
    # total annulées
    total_cancelled = base_qs.filter(status__in=CANCELLED_STATUSES).count()

    # stats du mois en cours
    today = timezone.now().date()
    month_start = today.replace(day=1)
    month_orders = base_qs.filter(created_at__date__gte=month_start)

    # on suppose qu’on a agreed_price ou computed_total_price
    total_revenue_month = (
        month_orders
        .aggregate(
            total=Sum(
                Case(
                    When(computed_total_price__isnull=False, then=F("computed_total_price")),
                    When(agreed_price__isnull=False, then=F("agreed_price")),
                    default=0,
                )
            )
        )["total"] or 0
    )

    # nombre de urgentes ce mois
    urgent_month_count = month_orders.filter(is_urgent=True).count()

    # --------- pagination ----------
    page_number = request.GET.get("page") or 1
    paginator = Paginator(orders, 20)  # 20 commandes par page
    orders_page = paginator.get_page(page_number)

    # --------- liste de services pour filtre ----------
    provider_services = (
        ServiceOffer.objects
        .filter(provider=user)
        .order_by("title")
    )

    context = {
        "orders_page": orders_page,
        "filters": {
            "status": status_filter,
            "urgent": urgent_only,
            "q": q,
            "from": date_from_raw,
            "to": date_to_raw,
            "service": service_id,
        },
        "stats": {
            "total_active": total_active,
            "total_done": total_done,
            "total_cancelled": total_cancelled,
            "total_revenue_month": total_revenue_month,
            "urgent_month_count": urgent_month_count,
        },
        "provider_services": provider_services,
    }
    return render(request, "services/provider_orders_list.html", context)



from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ServiceOffer

@login_required(login_url='login') # Redirige vers login si pas connecté
def my_services_dashboard(request):
    # On récupère TOUS les services du créateur (même les brouillons/pauses)
    services = ServiceOffer.objects.filter(provider=request.user).order_by('-created_at')

    return render(request, 'services/my_services_dashboard.html', {
        'services': services,
    })
    
    
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ServiceOrder

@login_required(login_url='login')
def client_orders_list(request):
    # Récupérer toutes les commandes du client, triées par date décroissante
    orders = ServiceOrder.objects.filter(client=request.user).select_related('service', 'provider').order_by('-created_at')

    # Séparation simple pour des onglets (optionnel, mais sympa pour l'UX)
    active_orders = orders.filter(status__in=['pending', 'accepted', 'in_progress', 'delivered'])
    completed_orders = orders.filter(status='completed')
    cancelled_orders = orders.filter(status__in=['cancelled', 'expired'])

    return render(request, 'services/client_orders_list.html', {
        'orders': orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
    })
    
from django.views.decorators.http import require_POST
from django.contrib import messages

@login_required
@require_POST
def client_order_delete(request, order_id):
    order = get_object_or_404(ServiceOrder, id=order_id, client=request.user)
    
    # Sécurité : On empêche la suppression si la commande est en cours
    # On autorise seulement si : En attente, Annulée, Terminée ou Rejetée
    if order.status in ['in_progress', 'accepted', 'delivered']:
        messages.error(request, "Impossible de supprimer une commande en cours de traitement.")
    else:
        order.delete()
        messages.success(request, "La commande a été supprimée de votre historique.")
        
    return redirect('client_orders_list')