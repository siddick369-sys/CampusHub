from datetime import timezone
from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from CampuHub.image_utils import optimize_image
from incubation.validators import valider_taille_image_2mo


# -------------------------------------------------------------------
#  MIXIN DE BASE (timestamps)
# -------------------------------------------------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -------------------------------------------------------------------
#  TAGS & FILIÈRES
# -------------------------------------------------------------------

class TrackTag(models.Model):
    """
    Tag de filière (ex: 'STEM', 'Management', 'Santé', 'Design').
    Sert pour filtrer et analyser.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Track(TimeStampedModel):
    """
    Filière / Parcours (ex: Informatique, Droit, Médecine...).
    Utilisée aussi par le module Stages (StageOffer.related_tracks).
    """
    DOMAIN_CHOICES = [
        ('stem', 'Sciences & Tech (STEM)'),
        ('business', 'Business & Management'),
        ('health', 'Santé'),
        ('social', 'Sciences sociales'),
        ('arts', 'Arts & Design'),
        ('other', 'Autre'),
    ]

    DIFFICULTY_CHOICES = [
        (1, 'Accessible'),
        (2, 'Modérée'),
        (3, 'Exigeante'),
        (4, 'Très exigeante'),
        (5, 'Élite'),
    ]

    OUTLOOK_CHOICES = [
        ('rising', 'Très porteur'),
        ('stable', 'Stable'),
        ('risky', 'En incertitude'),
    ]

    name = models.CharField(max_length=150, unique=True)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(unique=True)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Code interne (ex: INF-LIC, DRT-MAS...)."
    )

    domain = models.CharField(
        max_length=20,
        choices=DOMAIN_CHOICES,
        default='stem'
    )
    difficulty = models.PositiveSmallIntegerField(
        choices=DIFFICULTY_CHOICES,
        default=2
    )
    typical_duration_years = models.PositiveSmallIntegerField(
        default=3,
        help_text="Durée typique des études (en années)."
    )

    description = models.TextField(blank=True, null=True)
    main_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences techniques (séparées par des virgules)."
    )
    soft_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences humaines/comportementales."
    )
    recommended_profiles = models.TextField(
        blank=True,
        null=True,
        help_text="Quel type d'élève est le plus adapté à cette filière ?"
    )
    future_outlook = models.CharField(
        max_length=20,
        choices=OUTLOOK_CHOICES,
        default='rising',
        help_text="Avenir global de la filière."
    )

    tags = models.ManyToManyField(TrackTag, related_name='tracks', blank=True)

    color_hex = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Couleur (#3498db par ex) pour l'UI."
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nom d'icône (ex: 'fa-solid fa-laptop-code')."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
#  ÉCOLES & MÉTIERS
# -------------------------------------------------------------------

class School(TimeStampedModel):
    """
    École / Université proposant des filières.
    """

    SCHOOL_TYPE_CHOICES = [
        ('public', 'Public'),
        ('private', 'Privé'),
        ('online', 'En ligne'),
        ('other', 'Autre'),
    ]

    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to='schools/logos/', blank=True, null=True, validators=[valider_taille_image_2mo])

    school_type = models.CharField(
        max_length=20,
        choices=SCHOOL_TYPE_CHOICES,
        default='public'
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    tracks = models.ManyToManyField(Track, related_name='schools', blank=True)

    tuition_range = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Ex: '500k - 1M FCFA/an'."
    )
    admission_level = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Ex: Bac, Bac+2..."
    )

    ranking_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Score interne (0–10) pour classer les écoles."
    )

    is_partner = models.BooleanField(
        default=False,
        help_text="École partenaire officielle."
    )

    def save(self, *args, **kwargs):
        if self.logo:
            self.logo = optimize_image(self.logo)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Job(TimeStampedModel):
    """
    Métiers / débouchés liés aux filières.
    """

    DEMAND_LEVEL_CHOICES = [
        ('high', 'Très recherché'),
        ('medium', 'Recherché'),
        ('low', 'Peu demandé'),
    ]

    title = models.CharField(max_length=200)
    sector = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Secteur (IT, Finance, Santé...)."
    )
    description = models.TextField(blank=True, null=True)

    main_tasks = models.TextField(
        blank=True,
        null=True,
        help_text="Missions principales."
    )

    required_hard_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences techniques importantes."
    )
    required_soft_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences humaines (communication, équipe...)."
    )

    typical_salary_min = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Salaire de départ approximatif."
    )
    typical_salary_max = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Salaire après quelques années."
    )
    salary_currency = models.CharField(
        max_length=10,
        default='FCFA',
        blank=True
    )

    demand_level = models.CharField(
        max_length=10,
        choices=DEMAND_LEVEL_CHOICES,
        default='medium'
    )
    remote_friendly = models.BooleanField(
        default=False,
        help_text="Compatible télétravail ?"
    )

    tracks = models.ManyToManyField(
        Track,
        through='JobTrackRelevance',
        related_name='jobs',
        blank=True,
    )

    def __str__(self):
        return self.title


class JobTrackRelevance(models.Model):
    """
    Lien métier ↔ filière avec un score de pertinence.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    relevance_score = models.PositiveSmallIntegerField(
        default=3,
        help_text="1 = lien faible, 5 = lien très fort."
    )

    class Meta:
        unique_together = ('job', 'track')

    def __str__(self):
        return f"{self.job.title} ↔ {self.track.name} ({self.relevance_score}/5)"


# -------------------------------------------------------------------
#  TEST D’ORIENTATION
# -------------------------------------------------------------------

class Question(TimeStampedModel):
    """
    Question du test d'orientation.
    """

    CATEGORY_CHOICES = [
        ('interest', 'Centres d’intérêt'),
        ('skill', 'Compétences'),
        ('personality', 'Personnalité'),
        ('value', 'Valeurs / Priorités'),
    ]

    text = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='interest'
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.text[:50]}"


class Choice(TimeStampedModel):
    """
    Choix possible pour une question.
    Chaque choix donne des points à une ou plusieurs filières.
    """
    question = models.ForeignKey(
        Question,
        related_name='choices',
        on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    tracks = models.ManyToManyField(
        Track,
        through='ChoiceTrackScore',
        related_name='choice_links',
        blank=True
    )

    def __str__(self):
        return f"{self.text} (Q: {self.question_id})"


class ChoiceTrackScore(models.Model):
    """
    Score donné à une filière lorsqu'un choix est sélectionné.
    """
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    score = models.SmallIntegerField(
        default=1,
        help_text="Points ajoutés pour cette filière si ce choix est choisi."
    )

    class Meta:
        unique_together = ('choice', 'track')

    def __str__(self):
        return f"{self.choice.text[:20]} → {self.track.name} (+{self.score})"


# -------------------------------------------------------------------
#  RÉSULTATS & RÉPONSES
# -------------------------------------------------------------------

class OrientationResult(TimeStampedModel):
    """
    Résultat d'un test d'orientation pour un étudiant.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    suggested_tracks = models.ManyToManyField(
        Track,
        related_name='orientation_results',
        blank=True,
    )
    # JSON avec les scores :
    # {
    #   "tracks": {"3": 12, "5": 8},
    #   "categories": {"interest": 10, "skill": 6}
    # }
    scores_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Détails des scores (filières, catégories)."
    )

    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Note ou commentaire personnalisé."
    )

    def __str__(self):
        return f"Résultat pour {self.user.username} le {self.created_at.date()}"

    def get_sorted_tracks(self):
        """
        Retourne une liste [(track, score), ...] triée par score desc.
        """
        track_scores = (self.scores_data or {}).get("tracks", {}) or {}
        track_score_list = []
        for track in self.suggested_tracks.all():
            score = track_scores.get(str(track.id)) or track_scores.get(track.id) or 0
            track_score_list.append((track, score))
        return sorted(track_score_list, key=lambda x: x[1], reverse=True)


class OrientationAnswer(models.Model):
    """
    Réponse d'un utilisateur à une question dans un test donné.
    """
    result = models.ForeignKey(
        OrientationResult,
        related_name='answers',
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('result', 'question')

    def __str__(self):
        return f"{self.result.user.username} - {self.question.text[:30]}"
    
    
    
# -------------------------------------------------------------------
#  CONTENU PÉDAGOGIQUE (YouTube)
# -------------------------------------------------------------------

class YouTubePlaylist(TimeStampedModel):
    """
    Playlist YouTube liée à une ou plusieurs filières.
    """
    DIFFICULTY_CHOICES = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
    ]

    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'Anglais'),
        ('bilingual', 'Bilingue'),
    ]

    # Identification
    title = models.CharField(max_length=200)
    youtube_url = models.URLField(help_text="URL complète de la playlist YouTube")
    playlist_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID YouTube automatique (ex: PLxyz...)"
    )
    
    # Métadonnées
    description = models.TextField(blank=True, null=True)
    thumbnail_url = models.URLField(blank=True, null=True)
    channel_name = models.CharField(max_length=150)
    channel_url = models.URLField(blank=True, null=True)
    
    # Caractéristiques pédagogiques
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='beginner'
    )
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default='fr'
    )
    estimated_hours = models.PositiveIntegerField(
        default=0,
        help_text="Durée totale estimée (heures)"
    )
    video_count = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de vidéos dans la playlist"
    )
    
    # Relations
    tracks = models.ManyToManyField(
        Track,
        related_name='youtube_playlists',
        help_text="Filières associées à cette playlist"
    )
    
    # Statut
    is_active = models.BooleanField(default=True)
    is_free = models.BooleanField(default=True)
    last_verified = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['title']
        verbose_name = "Playlist YouTube"
        verbose_name_plural = "Playlists YouTube"

    def __str__(self):
        return f"{self.title} ({self.channel_name})"

    def save(self, *args, **kwargs):
        # Extraction automatique de l'ID YouTube
        if self.youtube_url and not self.playlist_id:
            import re
            match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', self.youtube_url)
            if match:
                self.playlist_id = match.group(1)
        super().save(*args, **kwargs)
        
    def get_embed_url(self):
        """
        Retourne une URL d'embed correcte pour :
        - une playlist  => /embed/videoseries?list=...
        - une vidéo     => /embed/<VIDEO_ID>
        - sinon         => l'URL brute
        """
        from urllib.parse import urlparse, parse_qs

        # Cas playlist (comme avant)
        if self.playlist_id:
            return f"https://www.youtube.com/embed/videoseries?list={self.playlist_id}"

        if self.youtube_url:
            parsed = urlparse(self.youtube_url)

            # Cas youtu.be/<id>
            if "youtu.be" in parsed.netloc:
                video_id = parsed.path.lstrip("/")
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"

            # Cas youtube.com/watch?v=<id>
            if "youtube.com" in parsed.netloc:
                query = parse_qs(parsed.query)
                video_id = query.get("v", [""])[0]
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"

        # Fallback : on renvoie l'URL telle quelle
        return self.youtube_url


    @property
    def display_duration(self):
        if self.estimated_hours == 0:
            return "Durée variable"
        elif self.estimated_hours == 1:
            return "1 heure"
        else:
            return f"{self.estimated_hours} heures"
        
        
        
class UserPlaylistProgress(TimeStampedModel):
    """
    Suivi de progression des utilisateurs dans les playlists.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    playlist = models.ForeignKey(YouTubePlaylist, on_delete=models.CASCADE)
    
    # Progression
    completed_videos = models.PositiveIntegerField(default=0)
    total_videos = models.PositiveIntegerField(default=0)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Engagement
    last_watched = models.DateTimeField(blank=True, null=True)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Notes personnelles
    user_rating = models.PositiveSmallIntegerField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        blank=True, null=True
    )
    personal_notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'playlist')
        verbose_name = "Progression Playlist"
        verbose_name_plural = "Progressions Playlists"

    def update_progress(self, videos_completed):
        self.completed_videos = videos_completed
        self.total_videos = self.playlist.video_count
        self.progress_percentage = (videos_completed / self.total_videos * 100) if self.total_videos > 0 else 0
        self.is_completed = self.progress_percentage >= 95
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        self.save()


class AIOrientationSession(TimeStampedModel):
    """
    Stocke une session de test d'orientation IA.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    history = models.JSONField(default=list, blank=True)
    is_finished = models.BooleanField(default=False)
    final_recommendation = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"AI Session {self.session_id} - {self.user.username}"