from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from .validators import valider_taille_fichier_5mo, valider_taille_image_2mo
from accounts.models import Profile 
from CampuHub.image_utils import optimize_image
import uuid

class ProjetInnovation(models.Model):
    # --- 1. CATÉGORIES ---
    SECTEURS = (
        ('TECH', 'Informatique & Technologie'),
        ('AGRO', 'Agriculture & Agroalimentaire'),
        ('IND', 'Industrie & Mécanique'),
        ('BTP', 'Génie Civil & Architecture'),
        ('ART', 'Art, Mode & Culture'),
        ('SERV', 'Services & Commerce'),
        ('SANTE', 'Santé & Bien-être'),
        ('AUTRE', 'Autre'),
    )

    STADES = (
        ('IDEE', 'J\'ai juste une idée 💡'),
        ('MVP', 'J\'ai un prototype / échantillon 🛠️'),
        ('LIVE', 'Le projet est déjà lancé 🚀'),
    )

    # --- IDENTIFIANTS ---
    porteur = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name="projets_innovants_crees",
        limit_choices_to={'role': 'student'}
    )
    
    equipe = models.ManyToManyField(
        Profile,
        related_name="projets_rejoints",
        limit_choices_to={'role': 'student'},
        blank=True
    )

    # --- INFOS GÉNÉRALES ---
    titre = models.CharField(max_length=100, verbose_name="Nom du projet")
    slug = models.SlugField(unique=True, blank=True)
    secteur = models.CharField(max_length=10, choices=SECTEURS, default='TECH', verbose_name="Domaine d'activité")
    stade = models.CharField(max_length=10, choices=STADES, default='IDEE')
    
    description_courte = models.CharField(max_length=255, verbose_name="Phrase d'accroche")
    description_complete = models.TextField(verbose_name="Détails du projet")

    # --- MÉDIAS ---
    image_couverture = models.ImageField(
        upload_to='projets/covers/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'png', 'webp','jpeg']), valider_taille_image_2mo],
        help_text="Format: JPG, PNG, WEBP. Max 2 Mo."
    )

    video_demo = models.URLField(blank=True, null=True, verbose_name="Lien Vidéo")
    
    dossier_projet = models.FileField(
        upload_to='projets/docs/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['pdf', 'ppt', 'pptx']), valider_taille_fichier_5mo],
        verbose_name="Dossier de présentation",
        help_text="Business Plan, Plaquette (Max 5Mo)."
    )

    # --- NOUVEAU : PRÉSENCE DIGITALE ---
    site_web = models.URLField(blank=True, null=True, verbose_name="Site Web / Portfolio")
    lien_instagram = models.URLField(blank=True, null=True, help_text="Ex: https://instagram.com/mon_projet")
    lien_linkedin = models.URLField(blank=True, null=True, help_text="Ex: https://linkedin.com/in/...")
    
    # --- CONTACT ---
    lien_whatsapp = models.URLField(
        blank=True, null=True, 
        help_text="Lien direct WhatsApp (ex: https://wa.me/2376...)"
    )

    # --- NOUVEAU : INDICATEURS & BESOINS ---
    est_en_recrutement = models.BooleanField(default=False, verbose_name="Je cherche des co-équipiers")
    cherche_financement = models.BooleanField(default=False, verbose_name="Je cherche des investisseurs")
    
    besoins = models.TextField(
        blank=True, 
        verbose_name="Détails des besoins",
        help_text="Ex: Financement, un développeur, un local, des conseils..."
    )
    
    competences_recherchees = models.ManyToManyField('Competence', blank=True, verbose_name="Profils recherchés")
    
    # --- STATS ---
    vues = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(Profile, related_name="projets_aimes", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.image_couverture:
            self.image_couverture = optimize_image(self.image_couverture)
        if not self.slug:
            # Génère un slug unique : "mon-projet-a1b2" pour éviter les bugs si 2 projets ont le même nom
            base_slug = slugify(self.titre)
            self.slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"
        super().save(*args, **kwargs)

    @property
    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return self.titre
from django.db import models
from django.core.validators import FileExtensionValidator
from .validators import valider_taille_fichier_5mo, valider_taille_image_2mo
from accounts.models import Profile 

class ChallengeEntreprise(models.Model):
    # On reprend les mêmes secteurs pour la cohérence
    SECTEURS = (
        ('TECH', 'Informatique & Tech'),
        ('AGRO', 'Agriculture & Agro.'),
        ('IND', 'Industrie & BTP'),
        ('ART', 'Design, Art & Mode'),
        ('MARKETING', 'Marketing & Vente'),
        ('STRAT', 'Stratégie & Gestion'),
        ('AUTRE', 'Autre'),
    )

    TYPES_CHALLENGE = (
        ('HACK', 'Hackathon / Dev (Tech)'),
        ('CREA', 'Concours Créatif (Design/Logo/Vidéo)'),
        ('ETUDE', 'Étude de Cas / Stratégie (Business)'),
        ('PROB', 'Résolution de Problème (Ingénierie)'),
    )

    FORMATS_RENDU = (
        ('PDF', 'Dossier PDF / SlideDeck'),
        ('VIDEO', 'Vidéo de présentation'),
        ('CODE', 'Code Source / Lien GitHub'),
        ('PHYSIQUE', 'Prototype Physique / Maquette'),
        ('LIBRE', 'Format Libre'),
    )

    entreprise = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE,
        related_name="challenges_lances",
        limit_choices_to={'role': 'company'}
    )
    
    # --- 1. QUOI ? (Le besoin) ---
    titre = models.CharField(max_length=150, verbose_name="Titre du Challenge")
    secteur = models.CharField(max_length=15, choices=SECTEURS, default='TECH')
    type_challenge = models.CharField(max_length=10, choices=TYPES_CHALLENGE, default='HACK')
    
    description = models.TextField(
        verbose_name="Description détaillée",
        help_text="Expliquez le contexte, le problème à résoudre et vos attentes."
    )
    
    # --- 2. RESSOURCES (Pour aider les étudiants) ---
    cahier_des_charges = models.FileField(
        upload_to='challenges/docs/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx']), valider_taille_fichier_5mo],
        verbose_name="Document Support (Brief / Cahier des charges)",
        help_text="Un document détaillé pour guider les étudiants (PDF, DOC). Max 5 Mo."
    )
    
    image_illustration = models.ImageField(
        upload_to='challenges/img/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'png', 'webp','jpeg']), valider_taille_image_2mo],
        help_text="Une image pour donner envie de participer."
    )
    
    # --- 3. ATTENTES & RÉCOMPENSES ---
    format_rendu = models.CharField(
        max_length=10, 
        choices=FORMATS_RENDU, 
        default='PDF',
        verbose_name="Format attendu pour la réponse"
    )

    competences_cibles = models.ManyToManyField(
        'Competence', 
        blank=True, 
        verbose_name="Compétences recherchées",
        help_text="Quels types d'étudiants ciblez-vous ?"
    )
    
    recompense = models.CharField(
        max_length=100, 
        verbose_name="À gagner (Récompense)",
        help_text="Soyez précis : 'Stage rémunéré', 'Chèque de 50.000 FCFA', 'Mentorat'..."
    )
    
    date_limite = models.DateTimeField(verbose_name="Date de fin")
    is_active = models.BooleanField(default=True)
    
    # --- LIENS ---
    participants = models.ManyToManyField(
        Profile, 
        through='ParticipationChallenge',
        related_name='challenges_participes'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.image_illustration:
            self.image_illustration = optimize_image(self.image_illustration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titre} - {self.entreprise.company_name}"
class ParticipationChallenge(models.Model):
    candidat = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    
    challenge = models.ForeignKey(ChallengeEntreprise, on_delete=models.CASCADE)
    
    # --- MODIFICATION ICI : Validation Fichier Rendu ---
    fichier_rendu = models.FileField(
        upload_to='rendus_challenges/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'zip', 'rar', 'doc', 'docx']),
            valider_taille_fichier_5mo
        ],
        help_text="Votre solution (PDF, ZIP, RAR). Max 5 Mo."
    )
    
    description_solution = models.TextField(blank=True, help_text="Explication rapide de la solution")
    lien_externe = models.URLField(blank=True, null=True, help_text="Lien GitHub ou Drive si fichier lourd")
    
    date_soumission = models.DateTimeField(auto_now_add=True)
    est_vainqueur = models.BooleanField(default=False)
    
    STATUT_RECOMPENSE = (
        ('PENDING', 'En attente'),
        ('SENT', 'Envoyé par l\'entreprise'),
        ('RECEIVED', 'Confirmé par l\'étudiant'),
        ('DISPUTE', 'Litige / Non reçu'),
    )
    
    statut_recompense = models.CharField(max_length=10, choices=STATUT_RECOMPENSE, default='PENDING')
    date_confirmation_etudiant = models.DateTimeField(null=True, blank=True)
    
    # Pour qu'un admin puisse trancher en cas de litige
    note_litige = models.TextField(blank=True, help_text="Explication du problème par l'étudiant")

    # ...
    feedback_entreprise = models.TextField(blank=True, null=True, help_text="Retour de l'entreprise sur ce travail")

    class Meta:
        unique_together = ('candidat', 'challenge')
        verbose_name = "Participation / Soumission"

    def __str__(self):
        return f"Soumission de {self.candidat.full_name} pour {self.challenge.titre}"
    
# incubateur/models.py

class ProjetUpdate(models.Model):
    projet = models.ForeignKey(
        ProjetInnovation, 
        on_delete=models.CASCADE, 
        related_name="actualites"
    )
    titre = models.CharField(max_length=150, verbose_name="Titre de l'actualité")
    contenu = models.TextField(verbose_name="Contenu")
    image = models.ImageField(
        upload_to='projets/updates/', 
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'png', 'webp']), valider_taille_image_2mo],
        help_text="Une photo pour illustrer cette étape (Optionnel)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Les plus récentes en haut
        verbose_name = "Actualité du projet"

    def save(self, *args, **kwargs):
        if self.image:
            self.image = optimize_image(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titre} ({self.projet.titre})"
    
    
# incubateur/models.py

class ChallengeSearchAlert(models.Model):
    user = models.ForeignKey(
        'accounts.Profile', # ou settings.AUTH_USER_MODEL selon ta config, ici Profile semble le mieux
        on_delete=models.CASCADE,
        related_name='search_alerts'
    )
    query = models.CharField(max_length=100, help_text="Le mot-clé recherché")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # On évite qu'un user enregistre 50 fois la même recherche "Python"
        unique_together = ('user', 'query') 

    def __str__(self):
        return f"Alerte '{self.query}' pour {self.user}"
    
    
class ProjetSearchAlert(models.Model):
    user = models.ForeignKey(
        'accounts.Profile', 
        on_delete=models.CASCADE,
        related_name='project_alerts'
    )
    query = models.CharField(max_length=100, help_text="Le mot-clé recherché")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'query')

    def __str__(self):
        return f"Alerte Projet '{self.query}' pour {self.user}"
    
    
    
from django.db import models

# On garde les compétences pour les tags visuels (facultatif mais recommandé pour le design)
class Competence(models.Model):
    nom = models.CharField(max_length=50)
    couleur = models.CharField(max_length=7, default="#3B82F6", help_text="Code Hex (ex: #3B82F6)")
    
    def __str__(self): 
        return self.nom

class EtudiantTalent(models.Model):
    noms_prenoms = models.CharField(max_length=200, verbose_name="Noms et Prénoms")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    adresse_email = models.EmailField(verbose_name="Adresse Email")
    filiere = models.CharField(max_length=100, verbose_name="Filière")
    moyenne_generale = models.FloatField(verbose_name="Moyenne Générale")
    
    # Champs pour le design (Photo et Tags)
    photo = models.ImageField(upload_to='talents/', blank=True, null=True, validators=[valider_taille_image_2mo])
    competences = models.ManyToManyField(Competence, blank=True)

    def save(self, *args, **kwargs):
        if self.photo:
            self.photo = optimize_image(self.photo)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-moyenne_generale'] # Trie par les meilleurs notes en premier

    def __str__(self):
        return self.noms_prenoms
    
    
    
    
from django.db import models
from django.contrib.auth.models import User

class InterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    target_role = models.CharField(max_length=100) # Ex: Développeur Python
    difficulty = models.CharField(max_length=20, choices=[('junior', 'Junior'), ('mid', 'Confirmé'), ('senior', 'Expert')])
    created_at = models.DateTimeField(auto_now_add=True)
    is_finished = models.BooleanField(default=False)
    cv_text = models.TextField(blank=True, verbose_name="Texte du CV")
    job_description = models.TextField(blank=True, verbose_name="Description de l'offre")
    # Pour stocker le rapport final
    final_report = models.TextField(blank=True, null=True) 
    score = models.IntegerField(default=0)
    feedback_global = models.TextField(blank=True, null=True) # Analyse finale de l'IA

    def __str__(self):
        return f"Interview {self.target_role} - {self.user.username}"

class ChatMessage(models.Model):
    session = models.ForeignKey(InterviewSession, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=[('user', 'Utilisateur'), ('ai', 'Coach IA')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)