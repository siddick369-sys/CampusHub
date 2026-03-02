from django.contrib import admin

from django.contrib import admin

from .utils_emails import send_provider_verified_email
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'role',
        'full_name',
        'city',
        'country',
        'is_verified',
        'email_verified',
        'created_at',
        'is_service_provider',
        'is_service_provider_verified',
        'trust_score',
        'kyc_verified',
        
    )
    list_filter = (
        'role',
        'is_verified',
        'city',
        'country',
        'created_at',
        'is_service_provider',
        'is_service_provider_verified',
        'kyc_verified',
        
    )
    search_fields = (
        'user__username',
        'user__email',
        'full_name',
        'company_name',
        'provider_title',
    )
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ("Utilisateur", {
            'fields': ('user', 'role', 'is_verified')
        }),
        ("Infos générales", {
            'fields': (
                'full_name',
                'phone',
                'city',
                'country',
                'address',
                'date_of_birth',
                'bio',
                'avatar',
            )
        }),
        ("confiance / sécurité",{
            'fields':(
                'trust_score','last_trust_update',
            )
        }),
        ("Étudiant", {
            'fields': (
                'student_school',
                'student_level',
                'student_field',
            )
        }),
        ("Entreprise", {
            'fields': (
                'company_name',
                'company_position',
                'company_website',
                'company_description',
            )
        }),
        ("Prestataire de services", {
            'fields': (
                'provider_title',
                'provider_category',
                'provider_experience_years',
                'provider_hourly_rate',
                'provider_is_available',
                'is_service_provider',
                'is_service_provider_verified',
                'kyc_verified',
            )
        }),
        ("Métadonnées", {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        On override save_model pour détecter le moment où
        is_service_provider_verified passe de False -> True.
        """
        was_verified_before = False

        if change and obj.pk:
            try:
                old_obj = Profile.objects.get(pk=obj.pk)
                was_verified_before = old_obj.is_service_provider_verified
            except Profile.DoesNotExist:
                was_verified_before = False

        # On sauvegarde normalement
        super().save_model(request, obj, form, change)

        # Si avant c'était False et maintenant c'est True -> on envoie l'email
        if not was_verified_before and obj.is_service_provider_verified:
            send_provider_verified_email(obj)

from django.contrib import admin
from django.utils import timezone

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Profile, CompanyVerificationRequest


def send_company_verified_email(company):
    """
    Envoie un email à l'entreprise pour lui annoncer que
    sa vérification a été approuvée.
    """
    if not company.email:
        return

    profile = getattr(company, "profile", None)
    base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")

    subject = "Votre entreprise est vérifiée sur CampusHub ✅"

    context = {
        "company": company,
        "profile": profile,
        "base_url": base_url,
    }

    # Si tu veux un joli template HTML, crée emails/company_verified.html
    try:
        html_message = render_to_string("emails/company_verified.html", context)
    except Exception:
        html_message = None

    # Version texte (fallback)
    message = (
        f"Bonjour {profile.company_name or company.username},\n\n"
        "Votre entreprise a été vérifiée avec succès par l'équipe CampusHub.\n\n"
        "Vous pouvez maintenant publier des offres visibles par les étudiants "
        "et bénéficier du badge 'Entreprise vérifiée ✅' sur vos annonces.\n\n"
        f"Accédez à votre tableau de bord : {base_url}/stages/company/dashboard/\n\n"
        "Merci de votre confiance,\n"
        "L'équipe CampusHub."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[company.email],
        fail_silently=True,
        html_message=html_message,
    )
    
    



@admin.register(CompanyVerificationRequest)
class CompanyVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("company", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("company__username", "company__email")

    actions = ["mark_approved", "mark_rejected"]

    def mark_approved(self, request, queryset):
        """
        - passe les demandes en 'approved'
        - met à jour profile.company_verified = True
        - envoie un email à l'entreprise
        """
        for req in queryset:
            # Met à jour la demande
            req.status = "approved"
            req.reviewed_at = timezone.now()
            req.save()

            # Met à jour le profil
            profile = getattr(req.company, "profile", None)
            if profile and not profile.company_verified:
                profile.company_verified = True
                profile.save(update_fields=["company_verified"])

            # Envoie l'email
            send_company_verified_email(req.company)

        self.message_user(request, "Les demandes sélectionnées ont été approuvées, et les entreprises notifiées.")
    mark_approved.short_description = "Approuver et vérifier les entreprises sélectionnées"

    def mark_rejected(self, request, queryset):
        """
        - passe les demandes en 'rejected'
        (tu peux ensuite remplir admin_comment à la main si tu veux)
        """
        updated = queryset.update(status="rejected", reviewed_at=timezone.now())
        self.message_user(request, f"{updated} demande(s) marquée(s) comme refusée(s).")
    mark_rejected.short_description = "Refuser les demandes sélectionnées"
    
    
    
from django.contrib import admin
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "role_target", "max_cv_monthly", "is_active")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "is_active", "start_date", "end_date")