from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.forms import ValidationError
from datetime import timedelta, time
import uuid

# -------------------------------------------------------------------
# Profile Model
# -------------------------------------------------------------------
class Profile(models.Model):
    # Rôles possibles
    ROLE_CHOICES = [
        ('student', 'Étudiant'),
        ('company', 'Entreprise'),
        ('provider', 'Prestataire de services'),
    ]

    LEVEL_CHOICES = [
        ('terminale', 'Terminale'),
        ('licence', 'Licence'),
        ('master', 'Master'),
        ('autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    
    # Infos générales
    full_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # État du compte
    email_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    
    # Préférences & Alerts
    receive_orientation_alerts = models.BooleanField(default=True)
    service_email_as_client = models.BooleanField(default=True)
    service_email_as_provider = models.BooleanField(default=True)
    
    # Confiance & KYC
    trust_score = models.IntegerField(default=50)
    last_trust_update = models.DateTimeField(blank=True, null=True)
    kyc_document = models.FileField(upload_to="kyc_docs/", blank=True, null=True)
    kyc_verified = models.BooleanField(default=False)
    
    # Spécifique Étudiant
    student_school = models.CharField(max_length=150, blank=True, null=True)
    student_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True, null=True)
    student_field = models.CharField(max_length=150, blank=True, null=True)
    
    # Spécifique Entreprise
    company_name = models.CharField(max_length=150, blank=True, null=True)
    company_position = models.CharField(max_length=150, blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_description = models.TextField(blank=True, null=True)
    company_verified = models.BooleanField(default=False)
    
    # Spécifique Prestataire
    provider_title = models.CharField(max_length=150, blank=True, null=True)
    provider_category = models.CharField(max_length=100, blank=True, null=True)
    provider_experience_years = models.PositiveIntegerField(blank=True, null=True)
    provider_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    provider_is_available = models.BooleanField(default=True)
    provider_unavailable_until = models.DateField(blank=True, null=True)
    provider_availability_notes = models.CharField(max_length=255, blank=True, null=True)
    is_service_provider = models.BooleanField(default=False)
    is_service_provider_verified = models.BooleanField(default=False)
    
    # QR & Documents
    qr_target_document = models.ForeignKey(
        'stages.StudentDocument', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='chosen_for_qr_profile'
    )
    
    # Onboarding
    show_onboarding = models.BooleanField(default=True)
    onboarding_completed = models.BooleanField(default=False)
    
    # Monétisation & Trial
    first_login_at = models.DateTimeField(blank=True, null=True)
    trial_expiration_date = models.DateTimeField(blank=True, null=True)
    trial_consumed = models.BooleanField(default=False)
    
    # Chat
    chat_manual_enabled = models.BooleanField(default=True)
    chat_start_time = models.TimeField(null=True, blank=True)
    chat_end_time = models.TimeField(null=True, blank=True)
    last_chat_seen = models.DateTimeField(blank=True, null=True)
    CHAT_ONLINE_GRACE = 5 # minutes
    
    # Métadonnées dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def display_role(self):
        return dict(self.ROLE_CHOICES).get(self.role, "Rôle non défini")

    def clean(self):
        super().clean()
        if self.chat_start_time and self.chat_end_time:
            if self.chat_start_time >= self.chat_end_time:
                raise ValidationError({"chat_end_time": "L'heure de fin doit être après l'heure de début."})
        
        if self.pk:
            try:
                old = Profile.objects.get(pk=self.pk)
                if old.company_verified and not self.company_verified:
                    raise ValidationError("Vous ne pouvez pas retirer la vérification d'une entreprise déjà vérifiée.")
            except Profile.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.full_name:
            parts = self.full_name.split(' ', 1)
            if len(parts) > 1:
                self.user.first_name, self.user.last_name = parts[0], parts[1]
            else:
                self.user.first_name, self.user.last_name = self.full_name, ""
            
            # Update User without triggering signals to avoid recursion
            User.objects.filter(pk=self.user.pk).update(
                first_name=self.user.first_name,
                last_name=self.user.last_name
            )
        super().save(*args, **kwargs)

    def is_now_in_chat_window(self):
        if not self.chat_start_time or not self.chat_end_time:
            return True
        now = timezone.localtime().time()
        start, end = self.chat_start_time, self.chat_end_time
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end

    @property
    def is_chat_available_now(self):
        if not self.is_now_in_chat_window() or not self.last_chat_seen:
            return False
        return (timezone.now() - self.last_chat_seen) <= timedelta(minutes=self.CHAT_ONLINE_GRACE)

    def get_completion_status(self):
        missing = []
        if not self.role: return False, ["role"]
        
        common = {'full_name': 'Nom complet', 'phone': 'Téléphone', 'city': 'Ville', 'country': 'Pays'}
        for f, label in common.items():
            if not getattr(self, f): missing.append(label)
            
        if self.role == 'student':
            for f, l in {'student_school': 'École', 'student_level': 'Niveau', 'student_field': 'Filière'}.items():
                if not getattr(self, f): missing.append(l)
        elif self.role == 'company':
            for f, l in {'company_name': 'Nom Entreprise', 'company_position': 'Poste', 'company_description': 'Description'}.items():
                if not getattr(self, f): missing.append(l)
        elif self.role == 'provider':
            for f, l in {'provider_title': 'Titre', 'provider_category': 'Catégorie', 'kyc_document': 'KYC'}.items():
                if not getattr(self, f): missing.append(l)
        
        return (len(missing) == 0), missing

# -------------------------------------------------------------------
# Monétisation Models
# -------------------------------------------------------------------
class SubscriptionPlan(models.Model):
    ROLE_TARGET = [
        ('student', 'Étudiant'),
        ('company', 'Entreprise'),
        ('provider', 'Prestataire'),
    ]
    name = models.CharField(max_length=50, unique=True)
    role_target = models.CharField(max_length=20, choices=ROLE_TARGET, default='student')
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Code interne (ex: FREE_STUDENT, PRO_PROVIDER)")
    description = models.TextField(blank=True, null=True)
    price = models.PositiveIntegerField(help_text="Prix mensuel en XAF")
    
    # Quotas
    max_cv_monthly = models.IntegerField(default=1)
    max_interviews_monthly = models.IntegerField(default=1)
    max_tests_monthly = models.IntegerField(default=1)
    max_projects_monthly = models.IntegerField(default=1)
    max_offers_monthly = models.IntegerField(default=1)
    max_services_active = models.IntegerField(default=1)
    
    # Provider Specific Quotas
    max_featured_services = models.IntegerField(default=0)
    max_urgent_orders_per_day = models.IntegerField(default=0)
    max_time_slots = models.IntegerField(default=10)
    
    # New Quotas for Refinement
    max_challenges_monthly = models.IntegerField(default=0, help_text="Nombre de challenges publiables par mois")
    max_search_alerts = models.IntegerField(default=1, help_text="Nombre d'alertes de recherche actives autorisées")

    # Features
    can_use_ai = models.BooleanField(default=False)
    has_premium_badge = models.BooleanField(default=False)
    priority_matching = models.BooleanField(default=False)
    has_analytics = models.BooleanField(default=False)
    
    is_default = models.BooleanField(default=False, help_text="Plan par défaut pour le rôle cible")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.price} XAF/mois)"

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_trial = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30)
        super().save(*args, **kwargs)

    def check_active(self):
        if self.end_date < timezone.now() and self.is_active:
            self.is_active = False
            self.save(update_fields=['is_active'])
        return self.is_active

    @property
    def is_expired(self):
        return timezone.now() > self.end_date

    def days_remaining(self):
        delta = self.end_date - timezone.now()
        return max(0, delta.days)

# -------------------------------------------------------------------
# Analytics & Success
# -------------------------------------------------------------------
class UsageTracking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_stats')
    action_type = models.CharField(max_length=50)
    count = models.PositiveIntegerField(default=0)
    reset_date = models.DateField()

    class Meta:
        unique_together = ('user', 'action_type', 'reset_date')

class SuccessStory(models.Model):
    CATEGORIES = [('student', 'Étudiant'), ('company', 'Entreprise'), ('provider', 'Prestataire')]
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=CATEGORIES)
    title = models.CharField(max_length=200)
    story = models.TextField()
    image = models.ImageField(upload_to='success_stories/', blank=True, null=True)
    date = models.DateField(default=timezone.now)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.title}"

# -------------------------------------------------------------------
# Badges & Gamification
# -------------------------------------------------------------------
class Badge(models.Model):
    nom = models.CharField(max_length=50)
    image = models.ImageField(upload_to='badges/')
    description = models.CharField(max_length=200)
    condition_obtention = models.CharField(max_length=100)

    def __str__(self):
        return self.nom

class UserBadge(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='badges_obtenus')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    date_obtention = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

# -------------------------------------------------------------------
# Requests
# -------------------------------------------------------------------
class CompanyVerificationRequest(models.Model):
    STATUS_CHOICES = [("pending", "En attente"), ("approved", "Approuvée"), ("rejected", "Refusée")]
    company = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_requests")
    document = models.FileField(upload_to="companies/verification_documents/")
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Vérification {self.company.username} – {self.status}"
