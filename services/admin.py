from django.contrib import admin

from .models import ServiceOffer, ServicePackage, ServiceExtra, ServiceOrder, FavoriteService, ServiceReview, ProviderPenaltyLog

# Register your models here.
from django.contrib import admin
from .models import (
    FavoriteService,
    ServiceCategory,
    ServiceTag,
    ServiceOffer,
    ServiceMedia,
    ServiceFAQ,
    ServiceOrder,
    ServiceOrderEvent,
    ServiceSearchAlert,
)


class ServicePackageInline(admin.TabularInline):
    model = ServicePackage
    extra = 1


class ServiceExtraInline(admin.TabularInline):
    model = ServiceExtra
    extra = 1




# -------------------------------
# CATÉGORIES & TAGS
# -------------------------------

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


# -------------------------------
# SERVICE OFFER
# -------------------------------

class ServiceMediaInline(admin.TabularInline):
    model = ServiceMedia
    extra = 1


class ServiceFAQInline(admin.TabularInline):
    model = ServiceFAQ
    extra = 1


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "category",
        "status",
        "visibility",
        "price_min",
        "price_max",
        "currency",
        "is_featured",
        "created_at",
    )
    list_filter = ("status", "visibility", "category", "is_featured")
    search_fields = ("title", "provider__username", "description")
    inlines = [ServiceMediaInline, ServiceFAQInline]
    
    inlines = [ServicePackageInline, ServiceExtraInline]
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)


# -------------------------------
# SERVICE ORDER
# -------------------------------

class ServiceOrderEventInline(admin.TabularInline):
    model = ServiceOrderEvent
    extra = 0
    readonly_fields = ("created_at",)
# services/admin.py
from django.contrib import admin
from .models import ProviderTimeSlot

@admin.register(ProviderTimeSlot)
class ProviderTimeSlotAdmin(admin.ModelAdmin):
    list_display = ("provider", "weekday", "start_time", "end_time", "capacity", "service")
    list_filter = ("provider", "weekday", "service")

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "service_title_snapshot",
        "provider",
        "client",
        "agreed_price",
        "currency",
        "status",
        "created_at",
        "due_date",
    )
    list_filter = ("status", "currency")
    search_fields = ("service_title_snapshot", "provider__username", "client__username")
    inlines = [ServiceOrderEventInline]
    ordering = ("-created_at",)


# -------------------------------
# ALERTES DE RECHERCHE
# -------------------------------

@admin.register(ServiceSearchAlert)
class ServiceSearchAlertAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "q",
        "category",
        "min_price",
        "max_price",
        "provider_city",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "category")
    search_fields = ("user__username", "q", "provider_city")
    ordering = ("-created_at",)
    
    
from django.contrib import admin
from .models import ProviderPenaltyLog


@admin.register(ProviderPenaltyLog)
class ProviderPenaltyLogAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "amount",
        "reason",
        "created_at",
    )
    list_filter = (
        "created_at",
        "reason",
    )
    search_fields = (
        "provider__username",
        "provider__email",
        "reason",
    )
    readonly_fields = (
        "provider",
        "amount",
        "reason",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        """On empêche d'ajouter des logs manuellement depuis l’admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Impossible de modifier les logs, seulement lecture."""
        return False
    
@admin.register(FavoriteService)
class ServiceFavoriteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "service",
        "created_at",
        "last_notified_at",
    )
    list_filter = (
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "service__title",
    )
    autocomplete_fields = ("user", "service")
    ordering = ("-created_at",)
    
    
    
from .models import ServiceSubscriptionPlan, ProviderSubscription

@admin.register(ServiceSubscriptionPlan)
class ServiceSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "max_active_services",
                    "max_featured_services", "is_default", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(ProviderSubscription)
class ProviderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("provider", "plan", "status", "start_date", "end_date", "auto_renew")
    list_filter = ("status", "plan")
    search_fields = ("provider__username", "provider__email")
    
    
from .models import ProviderFollow

@admin.register(ProviderFollow)
class ProviderFollowAdmin(admin.ModelAdmin):
    list_display = ("client", "provider", "created_at")
    search_fields = ("client__username", "provider__username")