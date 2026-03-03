from datetime import timedelta
from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import StageOffer, OfferImage

class OfferImageInline(admin.TabularInline):
    model = OfferImage
    extra = 1


from .models import StageOffer, StudentDocument, Application


@admin.register(StageOffer)
class StageOfferAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'company',
        'contract_type',
        'experience_level',
        'location_city',
        'location_country',
        'status',
        'is_active',
        'views_count',
        'applications_count',
        'created_at',
    )
    list_filter = (
        'contract_type',
        'experience_level',
        'location_type',
        'location_country',
        'status',
        'is_active',
        'created_at',
    )
    search_fields = (
        'title',
        'company__username',
        'company_name_snapshot',
        'location_city',
        'location_country',
        'reference',
    )
    inlines = [OfferImageInline]
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('related_tracks',)
    ordering = ('-created_at',)
    readonly_fields = ('views_count', 'applications_count', 'created_at', 'updated_at')

    fieldsets = (
        ("Infos générales", {
            "fields": (
                'company',
                'company_name_snapshot',
                'reference',
                'title',
                'slug',
                'contract_type',
                'experience_level',
                'status',
                'is_featured',
                'is_active',
            )
        }),
        ("Localisation", {
            "fields": (
                'location_city',
                'location_country',
                'location_type',
            )
        }),
        ("Détails contrat", {
            "fields": (
                'open_positions',
                'duration_months',
                'is_paid',
                'salary_min',
                'salary_max',
                'required_level',
                'language_requirements',
            )
        }),
        ("Profil recherché", {
            "fields": (
                'related_tracks',
                'skills_required',
                'skills_nice_to_have',
                'soft_skills_required',
            )
        }),
        ("Contenu de l'offre", {
            "fields": (
                'description',
                'responsibilities',
                'benefits',
            )
        }),
        ("Candidatures", {
            "fields": (
                'application_deadline',
                'max_applicants',
                'external_apply_url',
                'views_count',
                'applications_count',
            )
        }),
        ("Meta", {
            "fields": (
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'title',
        'doc_type',
        'language',
        'is_default_cv',
        'is_public',
        'created_at',
    )
    list_filter = ('doc_type', 'language', 'is_default_cv', 'is_public', 'created_at')
    search_fields = ('user__username', 'title', 'file')
    ordering = ('-created_at',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'offer',
        'student',
        'status',
        'rating',
        'is_withdrawn',
        'created_at',
        'status_changed_at',
        'viewed_at',
    )
    list_filter = ('status', 'is_withdrawn', 'source', 'created_at')
    search_fields = ('offer__title', 'student__username', 'offer__company__username')
    ordering = ('-created_at',)

    readonly_fields = (
        'created_at',
        'updated_at',
        'status_changed_at',
        'viewed_at',
        'withdrawn_at',
    )


from .models import StageOffer, StudentDocument, Application, Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    
    
from django.contrib import admin
from .models import QuickReply

@admin.register(QuickReply)
class QuickReplyAdmin(admin.ModelAdmin):
    list_display = ("label", "for_role", "owner", "is_global", "is_active", "created_at")
    list_filter = ("for_role", "is_global", "is_active")
    search_fields = ("label", "text", "owner__username", "owner__email")
    

    
    
    
from django.contrib import admin
from .models import CompanyFeedbacke


@admin.register(CompanyFeedbacke)
class CompanyFeedbackAdmin(admin.ModelAdmin):
    """
    Interface d’administration pour les avis laissés par les entreprises sur les étudiants.
    """
    list_display = (
        "company",
        "student",
        "short_content",
        "rating",
        "created_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = (
        "company__username",
        "student__username",
        "content",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Entreprise et étudiant", {
            "fields": ("company", "student")
        }),
        ("Contenu de l'avis", {
            "fields": ("content", "rating")
        }),
        ("Métadonnées", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )

    def short_content(self, obj):
        """Affiche un aperçu du contenu de l’avis."""
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content
    short_content.short_description = "Avis (aperçu)"

from django.contrib import admin
from django.utils.html import format_html
from .models import PlatformReview

@admin.register(PlatformReview)
class PlatformReviewAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste
    list_display = ('user', 'show_rating', 'role_at_review', 'is_approved', 'is_featured', 'created_at')
    
    # Filtres latéraux pour une gestion rapide
    list_filter = ('is_approved', 'is_featured', 'rating', 'role_at_review', 'created_at')
    
    # Recherche par nom d'utilisateur ou contenu du commentaire
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'comment')
    
    # Actions groupées (Approuver plusieurs avis d'un coup)
    actions = ['approve_reviews', 'disapprove_reviews', 'mark_as_featured']

    # Organisation des champs dans le formulaire d'édition
    fieldsets = (
        ('Informations Utilisateur', {
            'fields': ('user', 'role_at_review')
        }),
        ('Contenu de l\'Avis', {
            'fields': ('rating', 'comment')
        }),
        ('Modération & Visibilité', {
            'fields': ('is_approved', 'is_featured')
        }),
        ('Réponse de l\'Équipe CampusHub', {
            'fields': ('admin_response', 'responded_at'),
            'description': 'Laissez une réponse officielle qui sera visible sous l\'avis.'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    # --- LOGIQUE VISUELLE : Afficher des étoiles en couleur ---
    def show_rating(self, obj):
        stars = obj.rating
        html = '<span style="color: #ffc107;">' + ('★' * stars) + '</span>'
        html += '<span style="color: #e4e5e9;">' + ('★' * (5 - stars)) + '</span>'
        return format_html(html)
    show_rating.short_description = 'Note'

    # --- ACTIONS PERSONNALISÉES ---
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Les avis sélectionnés ont été approuvés.")
    approve_reviews.short_description = "Approuver les avis (Rendre public)"

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True, is_approved=True)
        self.message_user(request, "Les avis sélectionnés sont maintenant mis en avant.")
    mark_as_featured.short_description = "Mettre en avant sur la Home"

    # Enregistre automatiquement la date de réponse
    def save_model(self, request, obj, form, change):
        if obj.admin_response and not obj.responded_at:
            import datetime
            obj.responded_at = datetime.datetime.now()
        super().save_model(request, obj, form, change)


# ===== CV Generator Pro Admin =====
from .cv_models import (
    CVTemplate, CVProfile, CVVersion, CVExperience, CVEducation,
    CVSkill, CVLanguage, CVProject, CVCertification, CVInterest,
    CVScoreResult,
)


@admin.register(CVTemplate)
class CVTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_premium', 'is_active', 'sort_order')
    list_filter = ('is_premium', 'is_active')
    list_editable = ('sort_order', 'is_active')


class CVExperienceInline(admin.TabularInline):
    model = CVExperience
    extra = 0

class CVEducationInline(admin.TabularInline):
    model = CVEducation
    extra = 0

class CVSkillInline(admin.TabularInline):
    model = CVSkill
    extra = 0


@admin.register(CVProfile)
class CVProfileAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'version', 'is_primary', 'download_count', 'last_ats_score', 'updated_at')
    list_filter = ('is_primary', 'is_draft', 'template')
    search_fields = ('title', 'user__username', 'first_name', 'last_name')
    inlines = [CVExperienceInline, CVEducationInline, CVSkillInline]
    readonly_fields = ('download_count', 'view_count', 'applications_used_count')


@admin.register(CVScoreResult)
class CVScoreResultAdmin(admin.ModelAdmin):
    list_display = ('cv_profile', 'overall_score', 'keyword_score', 'action_verbs_score', 'created_at')
    list_filter = ('overall_score',)