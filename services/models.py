from django.db import models

# Create your models here.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from CampuHub.image_utils import optimize_image
from incubation.validators import valider_taille_image_2mo, valider_taille_fichier_5mo


# -------------------------------------------------------------------
# Base abstraite (si tu as déjà un TimeStampedModel global, tu peux
# utiliser le tien et supprimer celle-ci)
# -------------------------------------------------------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -------------------------------------------------------------------
# Catégories & Tags
# -------------------------------------------------------------------
class ServiceCategory(TimeStampedModel):
    """
    Catégorie principale de service (Design, Développement, Traduction…).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nom d’icône (ex: 'bi-code', 'fa-paint-brush'). Optionnel."
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    default_tags = models.ManyToManyField("ServiceTag", blank=True, related_name="default_for_categories",help_text="tags genere automatiquement pour cette categorie.",)

    class Meta:
        verbose_name = "Catégorie de service"
        verbose_name_plural = "Catégories de services"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ServiceTag(TimeStampedModel):
    """
    Tag libre pour affiner la recherche : 'logo', 'Laravel', 'UI/UX', etc.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Tag de service"
        verbose_name_plural = "Tags de services"
        ordering = ["name"]

    def __str__(self):
        return self.name


# -------------------------------------------------------------------
# Offre de service (ce que le prestataire propose)
# -------------------------------------------------------------------
class ServiceOffer(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("active", "Actif"),
        ("paused", "En pause"),
        ("archived", "Archivé"),
        ("blocked", "Bloqué par l’admin"),
    ]

    VISIBILITY_CHOICES = [
        ("public", "Visible dans la recherche"),
        ("unlisted", "Accessible seulement via le lien"),
    ]

    single_active_order = models.BooleanField(
        default=False,
        help_text=(
            "Si coché, ce service ne peut avoir qu'une seule commande active à la fois. "
            "Les nouvelles commandes sont bloquées tant qu'une commande en cours existe."
        ),
    )
    
    # ... tes champs actuels (title, price_min, etc.) ...

    # Durée d’un rendez-vous
    average_duration_minutes = models.PositiveIntegerField(
        default=60,
        null=True,
        blank=True,
        help_text="Durée typique d'une prestation (en minutes) pour un créneau réservé."
    )

    # Nombre max de clients en même temps sur un créneau
    slot_max_clients = models.PositiveIntegerField(
        default=1,
        help_text="Nombre maximum de clients que tu peux gérer en parallèle sur un même créneau."
    )

    # le reste de ton modèle...


    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_offers",
        help_text="Utilisateur qui propose ce service (étudiant, entreprise ou autre).",
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    # ... tes champs existants ...

    # 🔥 Options d’urgence
    allow_urgent = models.BooleanField(
        default=False,
        help_text="Accepter les demandes urgentes pour ce service."
    )
    urgent_extra_percent = models.PositiveIntegerField(
        default=20,
        help_text="Majoration en % pour une commande urgente (ex : 20 = +20%)."
    )
    urgent_max_per_day = models.PositiveIntegerField(
        default=3,
        help_text="Nombre max de commandes urgentes par jour (pour ce service)."
    )
    tags = models.ManyToManyField(
        ServiceTag,
        blank=True,
        related_name="services",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True,blank=True,help_text="Slug unique pour l'url du service")
    def _generate_unique_slug(self):
        """
        Génère un slug unique à partir du titre.
        Si le slug existe déjà, on ajoute -2, -3, etc.
        """
        base_slug = slugify(self.title or "")  # "Cours de maths" -> "cours-de-maths"
        if not base_slug:
            base_slug = "service"

        slug = base_slug
        counter = 2

        # On boucle tant qu'un autre ServiceOffer a déjà ce slug
        while ServiceOffer.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        # 🔹 On génère le slug une seule fois, à la création
        if not self.slug:
            self.slug = self._generate_unique_slug()
            
        
        if self.provider.profile.trust_score < 20:
            raise ValueError("Le prestataire n'a pas un score suffisant pour publier un service.")

        # ⚠️ IMPORTANT : on NE fait plus self.full_clean() ici
        super().save(*args, **kwargs)
        
    short_description = models.CharField(max_length=300)
    description = models.TextField()

    price_min = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Prix minimum en FCFA (ou autre devise)."
    )
    price_max = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Prix maximum en FCFA (ou autre devise)."
    )
    currency = models.CharField(max_length=10, default="FCFA")
    is_price_negotiable = models.BooleanField(
        default=False,
        help_text="Si actif, le client peut proposer un prix en dehors de la fourchette."
    )

    delivery_time_min_days = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Délai minimum (en jours) pour une commande standard."
    )
    delivery_time_max_days = models.PositiveIntegerField(
        default=14,
        validators=[MinValueValidator(1)],
        help_text="Délai maximum (en jours) que le prestataire accepte."
    )
    revisions_included = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Nombre de retours inclus dans le prix."
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default="public",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Permet de mettre certains services en avant dans la liste."
    )

    # stats / qualité
    average_rating = models.FloatField(
        default=0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
    )
    rating_count = models.PositiveIntegerField(default=0)
    completed_orders_count = models.PositiveIntegerField(default=0)
    last_order_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["status", "visibility", "is_featured"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["price_min", "price_max"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.provider.username})"

    # ---------- Validation business rules ----------
    def clean(self):
        errors = {}
        if self.price_min and self.price_max and self.price_min > self.price_max:
            errors["price_min"] = "Le prix minimum doit être inférieur ou égal au prix maximum."
        if self.delivery_time_min_days and self.delivery_time_max_days:
            if self.delivery_time_min_days > self.delivery_time_max_days:
                errors["delivery_time_min_days"] = "Le délai minimum doit être inférieur ou égal au délai maximum."
        if errors:
            raise ValidationError(errors)
        
    # ... tes champs existants, dont average_rating, rating_count ...

    def recompute_rating_stats(self):
        """
        Recalcule la moyenne et le nombre d'avis à partir de ServiceReview.
        """
        from django.db.models import Avg, Count

        agg = self.reviews.aggregate(
            avg=Avg("rating"),
            cnt=Count("id"),
        )
        self.average_rating = agg["avg"] or 0
        self.rating_count = agg["cnt"] or 0
        self.save(update_fields=["average_rating", "rating_count"])

    # ---------- Helpers ----------
    @property
    def is_active(self):
        return self.status == "active" and self.visibility == "public"

    def can_be_ordered(self):
        """
        Vrai si le service est commandable (status/visibility OK).
        """
        return self.status == "active"

    def update_rating(self):
        agg = self.reviews.aggregate(
            avg=models.Avg("rating"),
            count=models.Count("id"),
        )
        self.average_rating = agg["avg"] or 0
        self.rating_count = agg["count"] or 0
        self.save(update_fields=["average_rating", "rating_count"])

    def register_completed_order(self):
        self.completed_orders_count = models.F("completed_orders_count") + 1
        self.last_order_at = timezone.now()
        self.save(update_fields=["completed_orders_count", "last_order_at"])
        
    def create_default_packages(self):
        """
        Crée 3 packs par défaut (Basique / Standard / Premium) 
        si aucun pack n'existe encore pour ce service.
        """
        # import local pour éviter les problèmes d'ordre d'import
        from .models import ServicePackage  

        if self.packages.exists():
            return  # on ne recrée pas si ça existe déjà

        base_price = self.price_min or 0
        max_price = self.price_max or base_price

        # petites valeurs par défaut intelligentes
        basic_price = base_price
        standard_price = (base_price + max_price) // 2 if max_price > base_price else base_price
        premium_price = max_price

        ServicePackage.objects.bulk_create([
            ServicePackage(
                service=self,
                code="basic",
                title="Pack Basique",
                description="Version simple du service, idéale pour des besoins standard.",
                price=basic_price,
                delivery_time_days=self.delivery_time_max_days,
                revisions=self.revisions_included,
                sort_order=1,
                is_active=True,
            ),
            ServicePackage(
                service=self,
                code="standard",
                title="Pack Standard",
                description="Pack équilibré avec plus de suivi et de flexibilité.",
                price=standard_price,
                delivery_time_days=self.delivery_time_max_days,
                revisions=self.revisions_included + 1,
                sort_order=2,
                is_active=True,
            ),
            ServicePackage(
                service=self,
                code="premium",
                title="Pack Premium",
                description="Pack complet avec accompagnement renforcé et révisions supplémentaires.",
                price=premium_price,
                delivery_time_days=self.delivery_time_max_days,
                revisions=self.revisions_included + 2,
                sort_order=3,
                is_active=True,
            ),
        ])
    


# -------------------------------------------------------------------
# Médias & FAQ liés aux services
# -------------------------------------------------------------------
class ServiceMedia(TimeStampedModel):
    """
    Images / fichiers de présentation d’un service (portfolio).
    """
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("document", "Document"),
        ("video", "Vidéo (lien)"),
    ]

    service = models.ForeignKey(
        ServiceOffer,
        on_delete=models.CASCADE,
        related_name="media",
    )
    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        
    )
    image = models.ImageField(
        upload_to="services/images/",
        blank=True,
        null=True,
        validators=[valider_taille_image_2mo]
    )
    file = models.FileField(
        upload_to="services/files/",
        blank=True,
        null=True,
        validators=[valider_taille_fichier_5mo]
    )
    video_url = models.URLField(blank=True,null=True,help_text="URL YOUTUBE,ETC")

    caption = models.CharField(max_length=255, blank=True,help_text="Petit titre/description du media")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Média de service"
        verbose_name_plural = "Médias de services"
        ordering = ["sort_order", "created_at"]

    def save(self, *args, **kwargs):
        if self.image:
            self.image = optimize_image(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Média {self.media_type} pour {self.service.title}"
    
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# ... ServiceOffer, ServiceOrder, ServiceReview (qu'on a déjà) ...

from django.conf import settings
from django.db import models


class ProviderPenaltyLog(models.Model):
    """
    Journal des augmentations / diminutions de trust_score pour un prestataire.
    Permet d'expliquer les variations (support / admin).
    """
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_penalties"
    )
    amount = models.IntegerField(
        help_text="Nombre de points retirés (>0) ou ajoutés (<0)."
    )
    reason = models.CharField(
        max_length=255,
        help_text="Raison courte de la pénalité (affichable en admin)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "-" if self.amount > 0 else "+"
        return f"{self.provider.username} {sign}{abs(self.amount)} pts – {self.reason}"
    

class ServiceOrderReport(models.Model):
    """
    Signalement d'un problème sur une commande de service.
    Peut être fait par le client ou le prestataire.
    """
    STATUS_CHOICES = [
        ("open", "Ouvert"),
        ("in_review", "En cours de traitement"),
        ("resolved", "Résolu"),
        ("rejected", "Rejeté"),
    ]

    order = models.ForeignKey(
        "ServiceOrder",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    # ... tes champs actuels ...

    # Optionnel : rendez-vous planifié
    appointment_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Début du créneau réservé pour cette commande (si applicable)."
    )
    appointment_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fin du créneau réservé pour cette commande."
    )

    # ACTIVE_STATUSES tu l'as déjà
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_reports_made",
    )
    reported = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_reports_received",
    )

    reason = models.TextField(
        help_text="Expliquez le problème rencontré (escroquerie, non respect, insultes, etc.)."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("order", "reporter")  # 1 signalement max par personne / commande

    def __str__(self):
        return f"Signalement {self.id} – {self.reporter} → {self.reported} / commande {self.order_id}"
    
    



class ServiceFAQ(TimeStampedModel):
    """
    Questions/réponses fréquentes par service.
    """
    service = models.ForeignKey(
        ServiceOffer,
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "FAQ de service"
        verbose_name_plural = "FAQ de services"
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"FAQ pour {self.service.title}: {self.question[:40]}..."


# -------------------------------------------------------------------
# Services favoris (côté utilisateur)
# -------------------------------------------------------------------
class FavoriteService(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_services",
    )
    service = models.ForeignKey(
        ServiceOffer,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    last_notified_at = models.DateTimeField(blank=True, null=True, help_text="Pour ne pas spammer l'utilisateur")

    class Meta:
        verbose_name = "Service favori"
        verbose_name_plural = "Services favoris"
        unique_together = ("user", "service")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} ❤ {self.service.title}"

class ServiceSearchAlert(TimeStampedModel):
    """
    Alerte de recherche pour les services.
    Quand un service correspondant est publié, on notifie l'utilisateur.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_search_alerts",
    )

    # critères de recherche de base
    q = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_alerts",
    )
    min_price = models.PositiveIntegerField(null=True, blank=True)
    max_price = models.PositiveIntegerField(null=True, blank=True)
    provider_city = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Alerte de recherche de service"
        verbose_name_plural = "Alertes de recherche de services"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alerte service de {self.user.username}"
    
    

# -------------------------------------------------------------------
# Commandes & historique
# -------------------------------------------------------------------
class ServiceOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "En attente d'acceptation"),
        ("accepted", "Acceptée"),
        ("in_progress", "En cours"),
        ("delivered", "Livrée"),
        ("completed", "Terminée"),
        ("cancelled", "Annulée"),
        ("expired", "Expirée"),
    ]

    CANCELLATION_ACTOR_CHOICES = [
        ("client", "Client"),
        ("provider", "Prestataire"),
        ("platform", "Plateforme"),
    ]
    provider_mark_complete = models.BooleanField(
        default=False,
        help_text="Le prestataire a cliqué sur 'Terminer la commande'."
    )
    client_mark_complete = models.BooleanField(
        default=False,
        help_text="Le client a cliqué sur 'Terminer la commande'."
    )
    time_slot = models.ForeignKey('ProviderTimeSlot',null=True,blank=True, related_name='orders', on_delete=models.SET_NULL,help_text="creneau associe a un commancde")
    
    # ... tes champs existants ...

    # Snapshot de ce qui a été choisi au moment de la commande
    package_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Nom du pack choisi (Basique/Standard/Premium)."
    )
        # ... tes champs actuels ...

    is_urgent = models.BooleanField(
        default=False,
        help_text="Commande marquée comme urgente."
    )
    urgent_fee = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Montant de la majoration d’urgence."
    )
    total_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Prix total avec éventuellement l’urgence."
    )
    package_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Prix du pack choisi au moment de la commande."
    )
    extras_summary = models.TextField(
        blank=True,
        help_text="Résumé des options supplémentaires choisies."
    )
    extras_total_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total des extras choisis."
    )
    computed_total_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total pack + extras (indicatif)."
    )

    # reste de ta classe...

    # ...

    @property
    def is_fully_completed(self):
        return self.provider_mark_complete and self.client_mark_complete

    service = models.ForeignKey(
        ServiceOffer,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_orders",
        help_text="Utilisateur qui commande (client).",
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_sales",
        help_text="Utilisateur qui exécute (prestataire).",
    )

    # Snapshots pour garder l’historique même si le service change
    service_title_snapshot = models.CharField(max_length=255)
    provider_username_snapshot = models.CharField(max_length=150)

    description_brief = models.CharField(
        max_length=500,
        blank=True,
        help_text="Contexte fourni par le client pour cette commande."
    )

    agreed_price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        null=True,
        blank=True,
        help_text="Prix convenu en FCFA (ou autre devise)."
    )
    currency = models.CharField(max_length=10, default="FCFA")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    status_changed_at = models.DateTimeField(auto_now_add=True)

    # Paiement (à compléter plus tard si tu ajoutes un vrai système de paiement)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    # Délais
    due_date = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_actor = models.CharField(
        max_length=10,
        choices=CANCELLATION_ACTOR_CHOICES,
        blank=True,
    )
    cancellation_reason = models.TextField(blank=True)

    # Limite de révisions (snapshot depuis le service)
    max_revisions = models.PositiveIntegerField(default=0)
    revisions_used = models.PositiveIntegerField(default=0)

    # Lien optionnel vers ta messagerie (app "messaging")
    
    class Meta:
        verbose_name = "Commande de service"
        verbose_name_plural = "Commandes de services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["client"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        return f"Commande #{self.id} - {self.service_title_snapshot}"

    # ---------- Helpers sécurité ----------
    def is_client(self, user):
        return user and user.is_authenticated and user.id == self.client_id

    def is_provider(self, user):
        return user and user.is_authenticated and user.id == self.provider_id

    def can_user_view(self, user):
        return self.is_client(user) or self.is_provider(user)

    def can_user_manage(self, user):
        """
        Qui a le droit de changer le statut ?
        - provider : accepte, passe en cours, livre, finalise
        - client : peut marquer "reçu" / valider la complétion / demander annulation
        (La logique exacte se fera dans les vues, mais ce helper est là au cas où.)
        """
        return self.is_client(user) or self.is_provider(user)

    # ---------- Transitions de statut robustes ----------
    def change_status(self, new_status: str, actor=None, reason: str = ""):
        """
        Change le statut avec vérification des transitions autorisées
        et création d’un événement d’historique.
        """
        allowed_statuses = {c[0] for c in self.STATUS_CHOICES}
        if new_status not in allowed_statuses:
            raise ValueError("Statut de commande invalide")

        # Transitions autorisées
        allowed_transitions = {
            "pending": {"accepted", "cancelled"},
            "accepted": {"in_progress", "cancelled"},
            "in_progress": {"delivered", "cancelled"},
            "delivered": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }

        old_status = self.status
        if new_status == old_status:
            return  # rien à faire

        if new_status not in allowed_transitions.get(old_status, set()):
            raise ValueError(f"Transition de {old_status} vers {new_status} non autorisée")

        now = timezone.now()
        self.status = new_status
        self.status_changed_at = now

        if new_status == "delivered":
            self.delivered_at = now
        elif new_status == "completed":
            self.completed_at = now
            # comptabiliser la commande terminée côté service
            self.service.register_completed_order()
        elif new_status == "cancelled":
            self.cancelled_at = now
            if actor:
                if self.is_client(actor):
                    self.cancellation_actor = "client"
                elif self.is_provider(actor):
                    self.cancellation_actor = "provider"
                else:
                    self.cancellation_actor = "platform"
            if reason:
                self.cancellation_reason = reason

        self.save()

        ServiceOrderEvent.objects.create(
            order=self,
            event_type="status_change",
            actor=actor,
            from_status=old_status,
            to_status=new_status,
            message=reason or "",
        )


class ServiceOrderEvent(TimeStampedModel):
    """
    Historique des événements d'une commande :
    - changements de statut
    - messages système
    - demandes d’annulation, etc.
    """
    EVENT_TYPE_CHOICES = [
        ("status_change", "Changement de statut"),
        ("system", "Événement système"),
        ("note", "Note interne"),
    ]

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default="status_change",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_order_events",
    )

    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Événement de commande"
        verbose_name_plural = "Événements de commandes"
        ordering = ["created_at"]

    def __str__(self):
        return f"Event {self.event_type} pour commande #{self.order_id}"


# -------------------------------------------------------------------
# Avis sur les services
# -------------------------------------------------------------------
        
        
from django import forms
from .models import ServiceOrder


class ServiceOrderClientActionForm(forms.Form):
    """
    Formulaire pour le CLIENT d'une commande.
    Il peut :
      - marquer la commande comme 'completed'
      - demander l'annulation ('cancelled')
    selon le statut actuel.
    """
    ACTION_COMPLETE = "complete"
    ACTION_CANCEL = "cancel"

    ACTION_CHOICES = [
        (ACTION_COMPLETE, "Confirmer que le service est bien terminé"),
        (ACTION_CANCEL, "Demander l'annulation de la commande"),
    ]

    action = forms.ChoiceField(label="Que souhaitez-vous faire ?")
    reason = forms.CharField(
        label="Commentaire (optionnel, mais recommandé pour une annulation)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, order: ServiceOrder = None, **kwargs):
        self.order = order
        super().__init__(*args, **kwargs)

        choices = []
        if order is not None:
            # Si la commande est livrée → le client peut :
            #   - valider (completed)
            #   - demander l'annulation
            if order.status == "delivered":
                choices = self.ACTION_CHOICES

            # Si la commande est en cours mais pas livrée, il peut seulement annuler
            elif order.status in ("pending", "accepted", "in_progress"):
                choices = [
                    (self.ACTION_CANCEL, "Demander l'annulation de la commande"),
                ]

            # Si déjà 'completed' ou 'cancelled' → aucune action
            else:
                choices = []

        self.fields["action"].choices = choices

    def clean_action(self):
        action = self.cleaned_data.get("action")
        if not action:
            raise forms.ValidationError("Veuillez choisir une action.")
        # S'il n'y a pas d'action possible mais le client bricole le POST :
        if not self.fields["action"].choices:
            raise forms.ValidationError("Aucune action n'est possible pour cette commande.")
        return action

    def apply(self, actor):
        """
        Applique l'action choisie sur la commande :
          - 'complete'  -> status 'completed'
          - 'cancel'    -> status 'cancelled'
        Utilise ServiceOrder.change_status pour respecter les transitions
        et enregistrer l'historique.
        """
        if not self.order:
            return

        action = self.cleaned_data["action"]
        reason = self.cleaned_data.get("reason") or ""

        if action == self.ACTION_COMPLETE:
            # On demande à passer en 'completed'
            self.order.change_status("completed", actor=actor, reason=reason)

        elif action == self.ACTION_CANCEL:
            # On demande à passer en 'cancelled'
            self.order.change_status("cancelled", actor=actor, reason=reason)
            
            
    
    
from django.core.validators import MinValueValidator, MaxValueValidator

class ServiceReview(models.Model):
    """
    Avis laissé par le client après une commande terminée.
    Un avis = une commande (order).
    """
    order = models.OneToOneField(
        "ServiceOrder",
        on_delete=models.CASCADE,
        related_name="review",
        help_text="Commande associée à cet avis."
    )
    service = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Service évalué."
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_reviews",
        help_text="Client qui laisse l'avis.",
        null=True,
        blank=True,
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5."
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Commentaire (optionnel)."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Avis {self.rating}/5 sur {self.service.title} par {self.client.username}"

    def save(self, *args, **kwargs):
        """
        On override save pour mettre à jour la moyenne du service.
        """
        super().save(*args, **kwargs)
        self.service.recompute_rating_stats()

    def delete(self, *args, **kwargs):
        """
        Si on supprime l'avis, on recalcule aussi la moyenne.
        """
        service = self.service
        super().delete(*args, **kwargs)
        service.recompute_rating_stats()
        
        
class ServicePackage(models.Model):
    """
    Pack d'offre pour un service (Basique / Standard / Premium, etc.).
    """
    PACKAGE_CHOICES = [
        ("basic", "Pack Basique"),
        ("standard", "Pack Standard"),
        ("premium", "Pack Premium"),
    ]

    service = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="packages",
    )
    code = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES,
        default="basic",
        help_text="Type de pack (Basique / Standard / Premium)."
    )
    title = models.CharField(
        max_length=120,
        help_text="Nom affiché au client, ex: Pack Basique"
    )
    description = models.TextField(
        blank=True,
        help_text="Ce qui est inclus dans ce pack."
    )
    price = models.PositiveIntegerField(
        help_text="Prix proposé pour ce pack (en même devise que le service)."
    )
    delivery_time_days = models.PositiveIntegerField(
        default=1,
        help_text="Délai estimé pour ce pack."
    )
    revisions = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de révisions incluses pour ce pack."
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self):
        return f"{self.service.title} – {self.title}"


class ServiceExtra(models.Model):
    """
    Option supplémentaire associée à un service (ex : livraison express, fichiers sources, etc.).
    """
    service = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="extras",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(
        help_text="Surcoût si le client choisit cette option."
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.service.title} – Extra : {self.name}"
    
    
    
from django.conf import settings

class ProviderWeeklySlot(models.Model):
    """
    Créneau récurrent dans la semaine où le prestataire accepte des réservations.
    Optionnellement, lié à un service précis.
    """
    WEEKDAYS = [
        (0, "Lundi"),
        (1, "Mardi"),
        (2, "Mercredi"),
        (3, "Jeudi"),
        (4, "Vendredi"),
        (5, "Samedi"),
        (6, "Dimanche"),
    ]

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_slots",
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_parallel_orders = models.PositiveIntegerField(
        default=1,
        help_text="Nombre max de commandes simultanées dans ce créneau."
    )

    # Si renseigné : créneau spécifique à un service
    service = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="weekly_slots",
        null=True,
        blank=True,
        help_text="Si défini, ce créneau ne s'applique qu'à ce service."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["provider", "weekday", "start_time"]

    def __str__(self):
        base = f"{self.get_weekday_display()} {self.start_time}-{self.end_time}"
        if self.service:
            base += f" ({self.service.title})"
        return base
    
    
class ProviderVacation(models.Model):
    """
    Période où le prestataire ne prend pas de nouvelles commandes,
    même s'il a des créneaux hebdomadaires définis.
    """
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vacations",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True, null=True)

    affects_chat = models.BooleanField(
        default=True,
        help_text="Si coché, le prestataire est aussi considéré indisponible pour le chat."
    )

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.provider.username} en pause du {self.start_date} au {self.end_date}"
    
    
# services/models.py

from django.db import models
from django.conf import settings

class ProviderTimeSlot(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_slots"
    )

    # Jour (lundi → dimanche)
    weekday = models.IntegerField(
        choices=[
            (0, "Lundi"),
            (1, "Mardi"),
            (2, "Mercredi"),
            (3, "Jeudi"),
            (4, "Vendredi"),
            (5, "Samedi"),
            (6, "Dimanche"),
        ]
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    # Capacité max (3 clients dans le même créneau par ex.)
    capacity = models.PositiveIntegerField(default=1)

    # Pour réserver par service
    service = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="time_slots",
        null=True,
        blank=True
    )
    # ... tes champs existants ...
    # provider, service, weekday, start_time, end_time, capacity, etc.

    @property
    def active_bookings_count(self):
        """
        Nombre de commandes actives liées à ce créneau.
        On suppose que le related_name sur ServiceOrder est 'orders'.
        """
        ACTIVE_STATUSES = ["pending", "accepted", "in_progress"]
        return self.orders.filter(status__in=ACTIVE_STATUSES).count()

    @property
    def remaining_capacity(self):
        return max(0, self.capacity - self.active_bookings_count)

    @property
    def is_full(self):
        return self.active_bookings_count >= self.capacity

    class Meta:
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return (
            f"{self.provider} - {self.get_weekday_display()} "
            f"{self.start_time}-{self.end_time}"
        )
        
        
        
class ServiceSubscriptionPlan(models.Model):
    """
    Plan d'abonnement (Gratuit, Pro, Premium, etc.)
    Géré surtout par l'admin.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Code interne du plan (ex: FREE, PRO, PREMIUM)."
    )
    name = models.CharField(
        max_length=100,
        help_text="Nom affiché au prestataire."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description du plan / avantages."
    )
    monthly_price = models.PositiveIntegerField(
        default=0,
        help_text="Prix mensuel (ex: en FCFA). 0 = gratuit."
    )
    currency = models.CharField(
        max_length=10,
        default="FCFA",
    )

    # 🔒 Limites
    max_active_services = models.PositiveIntegerField(
        default=1,
        help_text="Nombre maximum de services actifs."
    )
    max_featured_services = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de services mis en avant autorisés."
    )
    max_urgent_orders_per_day = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de commandes urgentes par jour autorisées."
    )
    max_time_slots = models.PositiveIntegerField(
        default=10,
        help_text="Nombre maximal de créneaux (ProviderTimeSlot) que le prestataire peut créer."
    )

    highlight_in_search = models.BooleanField(
        default=False,
        help_text="Les services de ce plan remontent un peu plus dans les listes."
    )
    can_export_reports = models.BooleanField(
        default=False,
        help_text="Peut exporter des rapports (pdf/excel) sur ses commandes."
    )

    is_default = models.BooleanField(
        default=False,
        help_text="Plan par défaut pour tout nouveau prestataire."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plan d'abonnement"
        verbose_name_plural = "Plans d'abonnement"

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    
class ProviderSubscription(models.Model):
    """
    Abonnement d'un prestataire à un plan.
    Un prestataire peut avoir plusieurs lignes (historique),
    mais une seule active à la fois.
    """
    STATUS_CHOICES = [
        ("active", "Actif"),
        ("trial", "Essai"),
        ("cancelled", "Résilié"),
        ("expired", "Expiré"),
    ]

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_subscriptions",
    )
    plan = models.ForeignKey(
        ServiceSubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date de fin (optionnelle, pour plans sans reconduction)."
    )

    auto_renew = models.BooleanField(
        default=False,
        help_text="Renouveler automatiquement (géré par l'admin / système de paiement)."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # quelques stats simples
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes internes (ex: offert pour 3 mois, etc.)."
    )

    class Meta:
        verbose_name = "Abonnement prestataire"
        verbose_name_plural = "Abonnements prestataires"

    def __str__(self):
        return f"{self.provider.username} → {self.plan.code} ({self.status})"

    @property
    def is_currently_active(self):
        if self.status not in ["active", "trial"]:
            return False
        today = timezone.now().date()
        if self.end_date and self.end_date < today:
            return False
        return True
    
    
from django.conf import settings
from django.db import models

class ProviderFollow(models.Model):
    """
    Un client qui s'abonne à un prestataire de services.
    """
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followed_providers",
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "provider")
        verbose_name = "Abonnement prestataire"
        verbose_name_plural = "Abonnements prestataires"

    def __str__(self):
        return f"{self.client.username} suit {self.provider.username}"
    
    
    
    
    
from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils_notifications import (
    notify_followers_new_service,
    notify_followers_new_package,
)


@receiver(post_save, sender=ServiceOffer)
def serviceoffer_notify_followers_on_create(sender, instance, created, **kwargs):
    """
    Notifier les abonnés seulement :
    - si c'est une création
    - si le service est public + actif (ou publié, selon ton modèle)
    """
    if not created:
        return

    service = instance

    # adapte en fonction de tes valeurs réelles
    if getattr(service, "visibility", "") != "public":
        return
    if getattr(service, "status", "") not in ["active", "published"]:
        return

    notify_followers_new_service(service)


@receiver(post_save, sender=ServicePackage)
def servicepackage_notify_followers_on_create(sender, instance, created, **kwargs):
    """
    Notifier les abonnés lorsqu’un nouveau pack est créé.
    """
    if not created:
        return

    package = instance
    service = package.service

    # On peut décider de ne notifier que si le service est public/actif
    if getattr(service, "visibility", "") != "public":
        return
    if getattr(service, "status", "") not in ["active", "published"]:
        return

    notify_followers_new_package(service, package)
    
    
class ServiceCallSession(models.Model):
    service = models.OneToOneField(ServiceOffer, on_delete=models.CASCADE)
    room_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)