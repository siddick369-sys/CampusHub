"""
CV Generator Pro — Data Models
==============================
Comprehensive CV data models with versioning, analytics, scoring,
and premium template system.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


# -------------------------------------------------------------------
#  CV TEMPLATE (design catalogue)
# -------------------------------------------------------------------
class CVTemplate(models.Model):
    """Template de design disponible pour les CVs."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)
    preview_image = models.ImageField(upload_to='cv_templates/previews/', blank=True, null=True)
    template_file = models.CharField(
        max_length=200,
        help_text="Chemin du template HTML (ex: stages/cv_templates/modern.html)"
    )
    css_class = models.CharField(max_length=50, blank=True, help_text="Classe CSS racine")

    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Template CV"
        verbose_name_plural = "Templates CV"

    def __str__(self):
        return f"{self.name} {'⭐' if self.is_premium else ''}"


# -------------------------------------------------------------------
#  CV PROFILE (main record)
# -------------------------------------------------------------------
class CVProfile(models.Model):
    """Profil CV principal — un utilisateur peut en avoir plusieurs."""

    FONT_CHOICES = [
        ('inter', 'Inter'),
        ('roboto', 'Roboto'),
        ('playfair', 'Playfair Display'),
        ('lora', 'Lora'),
        ('montserrat', 'Montserrat'),
    ]
    PHOTO_FRAME_CHOICES = [
        ('circle', 'Cercle'),
        ('square', 'Carré'),
        ('rounded', 'Arrondi'),
        ('banner', 'Bande latérale'),
        ('none', 'Sans photo'),
    ]
    SKILL_DISPLAY_CHOICES = [
        ('bars', 'Barres de progression'),
        ('dots', 'Points'),
        ('text', 'Texte simple'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cv_profiles')
    title = models.CharField(max_length=100, default="Mon CV", verbose_name="Nom du CV")

    # --- Personal Info ---
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    professional_title = models.CharField(max_length=150, blank=True, verbose_name="Titre professionnel")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    photo = models.ImageField(upload_to='cv_photos/', blank=True, null=True)
    summary = models.TextField(blank=True, verbose_name="Résumé professionnel")

    # --- Design Preferences ---
    template = models.ForeignKey(CVTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#2563eb', help_text="Hex color")
    secondary_color = models.CharField(max_length=7, default='#1e293b')
    font_family = models.CharField(max_length=30, choices=FONT_CHOICES, default='inter')
    photo_frame = models.CharField(max_length=20, choices=PHOTO_FRAME_CHOICES, default='circle')
    skill_display = models.CharField(max_length=10, choices=SKILL_DISPLAY_CHOICES, default='bars')
    section_order = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordre des sections: ['experience','education','skills','languages','projects','certifications','interests']"
    )

    # --- State ---
    is_draft = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    job_category = models.CharField(max_length=100, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)

    # --- Analytics ---
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    applications_used_count = models.PositiveIntegerField(default=0)
    last_ats_score = models.PositiveIntegerField(blank=True, null=True, help_text="Dernier score ATS (0-100)")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Profil CV"
        verbose_name_plural = "Profils CV"

    def __str__(self):
        return f"{self.title} — {self.user.username} (v{self.version})"

    def get_template_path(self):
        if self.template:
            return self.template.template_file
        return 'stages/cv_templates/modern.html'

    def get_section_order(self):
        default = ['summary', 'experience', 'education', 'skills', 'languages', 'projects', 'certifications', 'interests']
        return self.section_order if self.section_order else default

    def increment_download(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def duplicate(self):
        """Crée une copie complète de ce CV."""
        # Clone all related objects
        experiences = list(self.experiences.all())
        educations = list(self.educations.all())
        skills = list(self.skills.all())
        languages = list(self.languages.all())
        projects = list(self.projects.all())
        certifications = list(self.certifications.all())
        interests = list(self.interests.all())

        # Clone the profile
        self.pk = uuid.uuid4()
        self.title = f"{self.title} (copie)"
        self.is_primary = False
        self.download_count = 0
        self.view_count = 0
        self.applications_used_count = 0
        self.version = 1
        self.save()

        # Clone related objects
        for obj_list in [experiences, educations, skills, languages, projects, certifications, interests]:
            for obj in obj_list:
                obj.pk = None
                obj.cv_profile = self
                obj.save()

        return self


# -------------------------------------------------------------------
#  CV VERSION HISTORY
# -------------------------------------------------------------------
class CVVersion(models.Model):
    """Snapshot historique d'un CV."""
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    snapshot_data = models.JSONField(help_text="Snapshot complet du CV en JSON")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ('cv_profile', 'version_number')

    def __str__(self):
        return f"v{self.version_number} — {self.cv_profile.title}"


# -------------------------------------------------------------------
#  REPEATABLE SECTIONS
# -------------------------------------------------------------------
class CVExperience(models.Model):
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='experiences')
    job_title = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.CharField(max_length=20, blank=True, help_text="Ex: 03/2024")
    end_date = models.CharField(max_length=20, blank=True, help_text="Ex: 08/2024 ou vide si en poste")
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    # Link to CampusHub stage application
    from_application = models.ForeignKey(
        'stages.Application', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Si créé automatiquement depuis une candidature CampusHub"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']

    def __str__(self):
        return f"{self.job_title} @ {self.company_name}"


class CVEducation(models.Model):
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='educations')
    diploma = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.CharField(max_length=20, blank=True)
    end_date = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']

    def __str__(self):
        return f"{self.diploma} — {self.institution}"


class CVSkill(models.Model):
    LEVEL_CHOICES = [
        (1, 'Débutant'),
        (2, 'Intermédiaire'),
        (3, 'Avancé'),
        (4, 'Expert'),
    ]
    CATEGORY_CHOICES = [
        ('technical', 'Technique'),
        ('soft', 'Humaine'),
    ]
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES, default=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='technical')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

    @property
    def level_percent(self):
        return self.level * 25


class CVLanguage(models.Model):
    LEVEL_CHOICES = [
        ('A1', 'A1 — Découverte'),
        ('A2', 'A2 — Survie'),
        ('B1', 'B1 — Seuil'),
        ('B2', 'B2 — Avancé'),
        ('C1', 'C1 — Autonome'),
        ('C2', 'C2 — Maîtrise'),
        ('native', 'Langue maternelle'),
    ]
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='languages')
    language = models.CharField(max_length=50)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='B1')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.language} ({self.level})"


class CVProject(models.Model):
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    technologies = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class CVCertification(models.Model):
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=150, blank=True)
    date = models.CharField(max_length=20, blank=True)
    url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class CVInterest(models.Model):
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='interests')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


# -------------------------------------------------------------------
#  CV SCORE ENGINE
# -------------------------------------------------------------------
class CVScoreResult(models.Model):
    """Résultat de l'analyse ATS d'un CV."""
    cv_profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='score_results')
    overall_score = models.PositiveIntegerField(help_text="Score global ATS 0-100")
    keyword_score = models.PositiveIntegerField(default=0)
    action_verbs_score = models.PositiveIntegerField(default=0)
    completeness_score = models.PositiveIntegerField(default=0)
    formatting_score = models.PositiveIntegerField(default=0)

    missing_keywords = models.JSONField(default=list, blank=True)
    suggestions = models.JSONField(default=list, blank=True)
    weak_descriptions = models.JSONField(default=list, blank=True)

    target_offer_title = models.CharField(max_length=255, blank=True, help_text="Offre ciblée pour l'optimisation")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Score {self.overall_score}/100 — {self.cv_profile.title}"
