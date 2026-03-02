from django.db import models

# Create your models here.
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse

from orientation.models import Track  # pour lier les offres aux filières déjà créées


# -------------------------------------------------------------------
#  Base abstraite : timestamps
# -------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """
    Ajoute automatiquement :
      - created_at : date de création
      - updated_at : dernière modification
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -------------------------------------------------------------------
#  OFFRES DE STAGE / ALTERNANCE / PREMIER EMPLOI
# -------------------------------------------------------------------

class StageOffer(TimeStampedModel):
    """
    Offre créée par une entreprise (utilisateur role='company').
    Modèle enrichi pour :
      - mieux filtrer
      - suivre les stats
      - mieux matcher avec les étudiants.
    """

    CONTRACT_CHOICES = [
        ('internship', 'Stage'),
        ('apprenticeship', 'Alternance'),
        ('job', 'Premier emploi'),
    ]

    LOCATION_TYPE_CHOICES = [
        ('onsite', 'Présentiel'),
        ('remote', 'À distance'),
        ('hybrid', 'Hybride'),
    ]

    EXPERIENCE_LEVEL_CHOICES = [
        ('none', 'Débutant / Sans expérience'),
        ('junior', 'Junior (0–2 ans)'),
        ('mid', 'Intermédiaire (2–5 ans)'),
    ]

    
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stage_offers',
        help_text="Utilisateur avec rôle 'company'."
    )

    # snapshot du nom d'entreprise pour éviter les surprises si le profil change
    company_name_snapshot = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Nom de l'entreprise au moment de la création de l'offre."
    )

    reference = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Référence interne de l'offre (ex: STG-2025-001)."
    )

    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_CHOICES,
        default='internship'
    )

    experience_level = models.CharField(
        max_length=10,
        choices=EXPERIENCE_LEVEL_CHOICES,
        default='none',
        help_text="Niveau d'expérience attendu."
    )

    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_country = models.CharField(max_length=100, blank=True, null=True)
    location_type = models.CharField(
        max_length=10,
        choices=LOCATION_TYPE_CHOICES,
        default='onsite'
    )

    open_positions = models.PositiveIntegerField(
        default=1,
        help_text="Nombre de postes à pourvoir."
    )

    duration_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Durée approximative en mois."
    )

    is_paid = models.BooleanField(default=True)
    salary_min = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Salaire / indemnité minimum (ex: en FCFA)."
    )
    salary_max = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Salaire / indemnité maximum."
    )

    required_level = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Niveau minimum (ex: Bac+1, Licence 2...)."
    )

    language_requirements = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Ex: Français courant, Anglais B2, bilingue..."
    )

    related_tracks = models.ManyToManyField(
        Track,
        blank=True,
        related_name='stage_offers',
        help_text="Filières qui correspondent bien à cette offre."
    )

    skills_required = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences techniques OBLIGATOIRES."
    )
    skills_nice_to_have = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences appréciées mais facultatives."
    )
    soft_skills_required = models.TextField(
        blank=True,
        null=True,
        help_text="Compétences humaines (rigueur, communication...)."
    )

    description = models.TextField()
    responsibilities = models.TextField(
        blank=True,
        null=True,
        help_text="Missions / responsabilités détaillées."
    )
    benefits = models.TextField(
        blank=True,
        null=True,
        help_text="Avantages (tickets resto, primes, formation...)."
    )

    
    external_apply_url = models.URLField(
        blank=True,
        null=True,
        help_text="Lien vers une page externe de candidature (si besoin)."
    )

    
    is_featured = models.BooleanField(
        default=False,
        help_text="Mettre en avant cette offre sur la page d'accueil."
    )

    # champs pour la data / analytique
    views_count = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de fois que l'offre a été vue."
    )
    

    application_deadline = models.DateField(
        blank=True,
        null=True,
        help_text="Date limite pour postuler."
    )
    max_applicants = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Nombre max de candidatures à accepter (optionnel)."
    )

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('published', 'Publiée'),
        ('archived', 'Archivée'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='published'
    )
    is_active = models.BooleanField(default=True)

    applications_count = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de candidatures reçues (mis à jour automatiquement)."
    )

    def _auto_update_status(self):
        """
        Ferme l'offre si la date limite est dépassée
        ou si le nombre max de candidatures est atteint.
        """
        today = timezone.now().date()
        expired = False

        # Date limite dépassée
        if self.application_deadline and today > self.application_deadline:
            expired = True

        # Nombre de candidatures dépassé
        if self.max_applicants is not None and self.applications_count >= self.max_applicants:
            expired = True

        if expired:
            self.is_active = False
            if self.status == 'published':
                self.status = 'archived'

    @property
    def is_open(self):
        """
        Offre encore ouverte aux candidatures ?
        """
        if not self.is_active or self.status != 'published':
            return False

        today = timezone.now().date()
        if self.application_deadline and today > self.application_deadline:
            return False

        if self.max_applicants is not None and self.applications_count >= self.max_applicants:
            return False

        return True
    
    def clean(self):
        super().clean()
        if not self.company_id:
            return
        if self.status == "published":
            profile = getattr(self.company, "profile", None)
            if not profile or not profile.company_verified:
                raise ValidationError("Votre entreprise doit être vérifiée pour publier une offre.")

    def save(self, *args, **kwargs):
        # On s'assure que la validation est appelée quand on sauve
        self.full_clean()  # peut lever ValidationError
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        # MAJ automatique avant d’enregistrer
        self._auto_update_status()
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.title} @ {self.company.username}"



    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    # ... les autres champs ...

    def save(self, *args, **kwargs):
        # Générer le slug seulement s'il est vide
        if not self.slug and self.title:
            base_slug = slugify(self.title)[:50]  # limite de longueur si tu veux
            slug = base_slug
            counter = 2

            # Boucle tant qu'un StageOffer possède déjà ce slug
            while StageOffer.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

# -------------------------------------------------------------------
#  DOCUMENTS ÉTUDIANTS (CV / PORTFOLIO / AUTRES)
# -------------------------------------------------------------------

class StudentDocument(TimeStampedModel):
    """
    Document de l'étudiant :
      - CV
      - Lettre de motivation type
      - Portfolio
      - Autre
    """

    DOC_TYPE_CHOICES = [
        ('cv', 'CV'),
        ('cover_letter', 'Lettre de motivation'),
        ('portfolio', 'Portfolio'),
        ('other', 'Autre'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    is_protected = models.BooleanField(
        default=True,
        help_text="Si coché, le fichier n'est accessible qu'à l'étudiant et aux personnes autorisées."
    )
    file = models.FileField(upload_to='students/documents/')

    title = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Nom du document (ex: 'CV 2025 FR', 'Portfolio design')."
    )

    doc_type = models.CharField(
        max_length=20,
        choices=DOC_TYPE_CHOICES,
        default='cv'
    )

    language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Langue principale du document (ex: Français, Anglais)."
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Notes internes pour l'étudiant (où il a utilisé ce doc, etc.)."
    )

    is_default_cv = models.BooleanField(
        default=False,
        help_text="CV principal à proposer par défaut lors d'une candidature."
    )

    is_public = models.BooleanField(
        default=False,
        help_text="Visible par les entreprises (ex: profil public)."
    )
    

    def __str__(self):
        return self.title or self.file.name
    
    


# -------------------------------------------------------------------
#  CANDIDATURES
# -------------------------------------------------------------------

class Application(TimeStampedModel):
    """
    Candidature d'un étudiant pour une offre.
    Enrichi :
      - suivi des dates (vue par l'entreprise, changement de statut)
      - possibilité de retrait
      - note interne / rating.
    """

    STATUS_CHOICES = [
        ('submitted', 'Envoyée'),
        ('viewed', 'Consultée'),
        ('shortlisted', 'Pré-sélectionné'),
        ('rejected', 'Refusée'),
        ('accepted', 'Acceptée'),
        ('withdrawn', 'Retirée par le candidat'),
    ]

    SOURCE_CHOICES = [
        ('platform', 'Trouvée sur CampusHub'),
        ('referral', 'Recommandation'),
        ('external', 'Lien externe'),
        ('other', 'Autre'),
    ]

    offer = models.ForeignKey(
        StageOffer,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    cv = models.ForeignKey(
        StudentDocument,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="CV utilisé pour cette candidature."
    )

    motivation_letter = models.TextField(
        blank=True,
        null=True,
        help_text="Lettre de motivation / message enregistré avec la candidature."
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )

    status_changed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Dernière fois où le statut a été mis à jour."
    )

    viewed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Quand l'entreprise a consulté la candidature."
    )

    is_withdrawn = models.BooleanField(
        default=False,
        help_text="Le candidat a-t-il retiré sa candidature ?"
    )
    withdrawn_at = models.DateTimeField(
        blank=True,
        null=True
    )

    company_note = models.TextField(
        blank=True,
        null=True,
        help_text="Notes internes de l'entreprise sur la candidature."
    )

    rating = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Note interne (1–5) donnée par l'entreprise au candidat."
    )
    

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='platform',
        help_text="Comment le candidat a découvert l'offre."
    )
    reminder_sent = models.BooleanField(default=False,help_text="rappel a deja ete envoyer a l'entreprise pour cette candidature.")
    applicant_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Empreinte de l'appareil (IP + User-Agent hashé) pour limiter les multi-comptes."
    )

    class Meta:
        unique_together = ('offer', 'student')

    def __str__(self):
        return f"Candidature {self.student.username} → {self.offer.title}"

from django.utils import timezone  # en haut du fichier si pas encore

class Notification(TimeStampedModel):
    """
    Notification envoyée à un utilisateur :
      - nouvelle candidature
      - changement de statut
      - rappel d'offre, etc.
    """
    NOTIF_TYPE_CHOICES = [
        ('new_application', 'Nouvelle candidature'),
        ('status_update', 'Mise à jour de candidature'),
        ('general', 'Notification générale'),
        ('message','Nouveau message prive'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notif_type = models.CharField(
        max_length=30,
        choices=NOTIF_TYPE_CHOICES,
        default='general'
    )
    message = models.TextField()

    offer = models.ForeignKey(
        StageOffer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications'
    )
    application = models.ForeignKey(
        'Application',  # référence par nom pour éviter les problèmes d'ordre
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications'
    )

    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notif pour {self.user.username} : {self.message[:40]}"


from django.db import models
from django.conf import settings

# ... tes autres imports et modèles ...
import re
from django.core.exceptions import ValidationError

class StageReview(TimeStampedModel):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    offer = models.ForeignKey(StageOffer, on_delete=models.CASCADE, related_name="reviews")
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_stage_reviews")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stage_reviews")
    application = models.OneToOneField("Application", on_delete=models.SET_NULL, blank=True, null=True, related_name="review")

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        unique_together = ("offer", "student")

    def clean(self):
        if self.comment:
            # Gibberish check (5 consonnes)
            if re.search(r'[^aeiouyáàâäéèêëíìîïóòôöúùûü\s]{5,}', self.comment, re.I):
                raise ValidationError({'comment': "Texte incohérent détecté."})
            # Répétitions (bla bla bla)
            if re.search(r'(\b\w+\b)( \1){2,}', self.comment, re.I):
                raise ValidationError({'comment': "Évitez les répétitions excessives."})


from django.db import models
from django.conf import settings

# ... tu as déjà TimeStampedModel dans ce fichier ...

from django.conf import settings

# ...

class QuickReply(TimeStampedModel):
    """
    Modèle de réponse rapide pour la messagerie.
    - Peut être globale (créée par l'admin) ou propre à une entreprise.
    """
    ROLE_CHOICES = [
        ("company", "Entreprise"),
        ("student", "Étudiant"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quick_replies",
        blank=True,
        null=True,
        help_text="Propriétaire de ce modèle. Null = modèle global (admin)."
    )
    label = models.CharField(
        max_length=100,
        help_text="Nom court (ex: 'Merci candidature')."
    )
    text = models.TextField(
        help_text="Texte qui sera inséré dans le chat."
    )
    for_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        null=True,
        help_text="Rôle ciblé (company / student). Null = tous."
    )
    is_global = models.BooleanField(
        default=False,
        help_text="Si coché, visible pour tous les utilisateurs du rôle ciblé."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Réponse rapide"
        verbose_name_plural = "Réponses rapides"

    def __str__(self):
        dest = self.for_role or "tous"
        return f"[{dest}] {self.label}"
class Conversation(TimeStampedModel):
    """
    Conversation interne :
      - soit liée à une Application (stages)
      - soit liée à une ServiceOrder (services)
    """

    # 🔹 Candidature (stages) — maintenant OPTIONNELLE
    application = models.OneToOneField(
        "Application",
        on_delete=models.CASCADE,
        related_name="conversation",
        blank=True,
        null=True,
        help_text="Conversation liée à une candidature de stage"
    )

    # 🔹 Commande de service (services) — OPTIONNELLE
    service_order = models.OneToOneField(
        "services.ServiceOrder",
        on_delete=models.CASCADE,
        related_name="conversation",
        blank=True,
        null=True,
        help_text="Conversation liée à une commande de service"
    )

    # Participants
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_conversations"
    )
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_conversations"
    )

    is_active = models.BooleanField(default=True)
    student_strike_count = models.PositiveIntegerField(default=0)
    company_strike_count = models.PositiveIntegerField(default=0)
    student_muted_until = models.DateTimeField(blank=True, null=True)
    company_muted_until = models.DateTimeField(blank=True, null=True)
    company_last_reminder_at = models.DateTimeField(blank=True, null=True)
    student_last_reminder_at = models.DateTimeField(blank=True, null=True)
    is_archived_student = models.BooleanField(default=False)
    is_archived_company = models.BooleanField(default=False)
    # 🆕 AJOUT : Lien vers le module Incubateur
    participation = models.OneToOneField(
        "incubation.ParticipationChallenge", # Utilise le chemin string pour éviter les imports circulaires
        on_delete=models.CASCADE,
        related_name="conversation",
        blank=True,
        null=True,
        help_text="Conversation liée à une soumission validée d'un challenge"
    )
    
    # exemple minimal :
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    # etc.

    # (les méthodes archive_for_user, unarchive_for_user, etc, restent pareil)

    def __str__(self):
        # affichage plus générique
        context = "Stage"
        if self.service_order_id:
            context = f"ServiceOrder {self.service_order_id}"
        elif self.application_id:
            context = f"Application {self.application_id}"
        return f"Conv {self.id} – {self.student.username} ↔ {self.company.username} ({context})"
    """
    Conversation entre une entreprise et un étudiant,
    liée à une candidature spécifique.
    """
    
    def archive_for_user(self, user):
        """
        Archive la conversation pour l'utilisateur donné, sans l'affecter pour l'autre.
        """
        if user.id == self.student_id:
            self.is_archived_student = True
        elif user.id == self.company_id:
            self.is_archived_company = True
        self.save(update_fields=["is_archived_student", "is_archived_company"])

    def unarchive_for_user(self, user):
        """
        Désarchive la conversation pour l'utilisateur donné.
        """
        if user.id == self.student_id:
            self.is_archived_student = False
        elif user.id == self.company_id:
            self.is_archived_company = False
        self.save(update_fields=["is_archived_student", "is_archived_company"])

    def is_archived_for_user(self, user):
        if user.id == self.student_id:
            return self.is_archived_student
        if user.id == self.company_id:
            return self.is_archived_company
        return False

    def is_user_muted(self, user):
        now = timezone.now()
        if user_id := getattr(user, "id", None):
            if user_id == self.student_id and self.student_muted_until:
                return self.student_muted_until > now
            if user_id == self.company_id and self.company_muted_until:
                return self.company_muted_until > now
        return False

    def add_strike_for_user(self, user, mute_after=1, mute_duration_minutes=1):
        """
        Incrémente le compteur de strikes pour l'utilisateur,
        et le mute s'il atteint le seuil.
        Retourne True si mute appliqué.
        """
        from django.utils import timezone
        changed = False
        now = timezone.now()

        if user.id == self.student_id:
            self.student_strike_count += 1
            if self.student_strike_count >= mute_after:
                self.student_muted_until = now + timezone.timedelta(minutes=mute_duration_minutes)
                changed = True
        elif user.id == self.company_id:
            self.company_strike_count += 1
            if self.company_strike_count >= mute_after:
                self.company_muted_until = now + timezone.timedelta(minutes=mute_duration_minutes)
                changed = True

        self.save(update_fields=[
            "student_strike_count",
            "company_strike_count",
            "student_muted_until",
            "company_muted_until",
        ])
        return changed
    
    
    
    # tout ce que tu as déjà

    @property
    def context_type(self):
        """
        Retourne 'service' si liée à une ServiceOrder,
        'stage' si liée à une Application,
        sinon 'other'.
        """
        if self.service_order_id:
            return "service"
        if self.application_id:
            return "stage"
        # 🆕 AJOUT
        if self.participation_id:
            return "challenge"
        return "other"

    @property
    def context_title(self):
        """
        Titre lisible selon le type de conversation.
        """
        if self.service_order_id and self.service_order:
            return f"Service : {self.service_order.service_title_snapshot}"
        if self.application_id and self.application:
            # adapte si ton modèle Application a un lien vers StageOffer
            try:
                return f"Stage : {self.application.offer.title}"
            except Exception:
                return f"Candidature #{self.application_id}"
        # 🆕 AJOUT : Titre pour le challenge
        if self.participation_id and self.participation:
            return f"Challenge : {self.participation.challenge.titre}"
        return "Conversation"

    @property
    def other_user_for(self, user):
        """
        Retourne l'autre participant (company ou student) pour un user donné.
        """
        if user.id == self.student_id:
            return self.company
        if user.id == self.company_id:
            return self.student
        return None

    def get_absolute_url(self):
        """
        URL pour afficher la conversation dans ton module messaging.
        Adapte 'messaging_conversation_detail' au nom réel de ta vue détail.
        """
        return reverse("messaging_conversation_detail", args=[self.id])

    def __str__(self):
        context = "Stage"
        if self.service_order_id:
            context = f"ServiceOrder {self.service_order_id}"
        elif self.application_id:
            context = f"Application {self.application_id}"
        elif self.participation_id:
            context = f"Challenge {self.participation.challenge.titre}"
        return f"Conv {self.id} – {self.student.username} ↔ {self.company.username} ({context})"

    

class Message(TimeStampedModel):
    """
    Message dans une conversation interne CampusHub.
    
    """
    
    MSG_TYPE_CHOICES = [
        ("normal", "Message normal"),
        ("systeme", "Message système")
    ]
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    
    # ... ce que tu as déjà (conversation, sender, text, msg_type, is_read, etc.)

    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)

    @property
    def display_text(self):
        """
        Texte à afficher dans le chat.
        """
        if self.is_deleted:
            return "Message supprimé"
        return self.text or ""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    text = models.TextField(blank=True)
    # ⚠️ Nouveau : pièce jointe
    attachment = models.FileField(
        upload_to="chat_attachments/",
        blank=True,
        null=True,
        max_length=255,
        help_text="Fichier envoyé dans le chat (image, PDF, doc...)."
    )
    attachment_mime = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Type MIME détecté"
    )
    attachment_size = models.PositiveIntegerField(
        default=0,
        help_text="Taille du fichier en octets"
    )
    is_read = models.BooleanField(default=False)
    msg_type = models.CharField(max_length=20,choices = MSG_TYPE_CHOICES,default="normal",help_text="Permet de distinguer les messages nirmaux des messages systeme"
    )
    

    def __str__(self):
        return f"Message {self.id} – {self.sender.username} ({self.created_at})"
    
    

class ConversationBlock(TimeStampedModel):
    """
    Un utilisateur qui bloque l'autre dans une conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="blocks"
    )
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received"
    )

    class Meta:
        unique_together = ("conversation", "blocker", "blocked")

    def __str__(self):
        return f"{self.blocker} bloque {self.blocked} dans conv {self.conversation_id}"


class ConversationReport(TimeStampedModel):
    """
    Signalement d'un utilisateur dans une conversation (abus, harcèlement, fraude).
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="reports"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_made"
    )
    reported = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_received"
    )
    reason = models.TextField()

    def __str__(self):
        return f"Report {self.id} – {self.reporter} → {self.reported}"


# stages/models.py
from django.conf import settings
from django.db import models

# ... tes autres imports / modèles ...

class SavedOffer(TimeStampedModel):
    """
    Offre sauvegardée (favori) par un étudiant.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_offers"
    )
    offer = models.ForeignKey(
        StageOffer,
        on_delete=models.CASCADE,
        related_name="saved_by_students"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Offre sauvegardée"
        verbose_name_plural = "Offres sauvegardées"
        unique_together = ("student", "offer")  # une seule fois par étudiant

    def __str__(self):
        return f"{self.student.username} a sauvegardé {self.offer.title}"
    
    
# stages/models.py
from django.conf import settings
from django.db import models

# ... tes autres modèles ...

class JobSearchAlert(TimeStampedModel):
    """
    Alerte créée quand un étudiant fait une recherche sans résultat.
    Exemple : 'emploi plein temps en informatique à Douala'.
    Quand une nouvelle offre correspond, on lui envoie un email.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_search_alerts",
    )

    # Paramètres de recherche bruts
    q = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Mot-clé (titre, compétences, description)."
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Ville recherchée (ex: Douala)."
    )
    contract_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Type de contrat (ex: full_time, internship...)."
    )
    location_type = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="remote / onsite / hybrid."
    )

    # Meta pour gestion de l’alerte
    is_active = models.BooleanField(default=True)
    last_matched_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Alerte de recherche d'offre"
        verbose_name_plural = "Alertes de recherche d'offres"

    def __str__(self):
        parts = []
        if self.q:
            parts.append(self.q)
        if self.city:
            parts.append(self.city)
        if self.contract_type:
            parts.append(self.contract_type)
        return f"Recherche de {self.student.username} : " + " / ".join(parts)
    
    
# companies/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


# -------------------------------------------------------------------
#  IMAGES / FEEDBACKS / REVIEWS
# -------------------------------------------------------------------
    
    
# models.py
class OfferImage(models.Model):
    offer = models.ForeignKey(StageOffer, related_name='images', on_delete=models.CASCADE)
    file = models.ImageField(upload_to='offers_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image pour {self.offer.title}"
    
    
class CompanyFeedbacke(TimeStampedModel):
    """
    Avis laissé par une entreprise sur une candidature ou un étudiant.
    """
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_feedbacks",
        help_text="Entreprise qui a laissé l'avis."
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_feedbacks",
        help_text="Étudiant concerné.",
        default=1
    )
    content = models.TextField(help_text="Contenu de l'avis laissé par l'entreprise.",default="Aucun Avis laisser")
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Avis de {self.company.username} sur {self.student.username}"
    
    
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Avg

class PlatformReview(models.Model):
    # Lien utilisateur
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='platform_reviews')
    
    # Snapshot du rôle au moment de l'avis (Étudiant, Entreprise ou Prestataire)
    ROLE_CHOICES = [
        ('student', 'Étudiant'),
        ('company', 'Entreprise'),
        ('provider', 'Prestataire de services')
    ]
    role_at_review = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Contenu
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1200)

    # Modération et Mise en avant
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Afficher sur la page d'accueil")
    
    # Interaction avec l'Admin
    admin_response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user',) # Un seul avis par personne (mais modifiable)

    def __str__(self):
        return f"{self.user.username} ({self.rating}/5)"

    # POINT 4 : Calcul de la moyenne globale
    @classmethod
    def get_global_stats(cls):
        stats = cls.objects.filter(is_approved=True).aggregate(
            avg=Avg('rating'),
            count=models.Count('id')
        )
        return {
            'average': round(stats['avg'] or 0, 1),
            'total': stats['count']
        }