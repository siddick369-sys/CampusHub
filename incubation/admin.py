from django.contrib import admin

# Register your models here.


from django.contrib import admin
from django.utils.html import format_html
from .models import Competence, ProjetInnovation, ChallengeEntreprise, ParticipationChallenge

@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'apercu_couleur')
    search_fields = ('nom',)

    def apercu_couleur(self, obj):
        # Affiche un petit carré de la couleur choisie
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 4px; border: 1px solid #ccc;"></div>',
            obj.couleur
        )
    apercu_couleur.short_description = "Couleur"

@admin.register(ProjetInnovation)
class ProjetInnovationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'porteur', 'stade', 'date_creation', 'nb_likes')
    list_filter = ('stade', 'created_at')
    search_fields = ('titre', 'porteur__full_name', 'porteur__user__username')
    
    # Pour gérer facilement les ManyToMany (Compétences et Équipe)
    filter_horizontal = ('competences_recherchees', 'equipe', 'likes')
    
    # Génère le slug automatiquement si tu le changes dans l'admin
    prepopulated_fields = {'slug': ('titre',)}
    
    def date_creation(self, obj):
        return obj.created_at.strftime("%d/%m/%Y")
        
    def nb_likes(self, obj):
        return obj.likes.count()
    nb_likes.short_description = "J'aime"

class ParticipationInline(admin.TabularInline):
    """Permet de voir les participants directement dans la fiche du Challenge"""
    model = ParticipationChallenge
    extra = 0
    readonly_fields = ('date_soumission',)
    can_delete = False

@admin.register(ChallengeEntreprise)
class ChallengeEntrepriseAdmin(admin.ModelAdmin):
    list_display = ('titre', 'entreprise', 'date_limite', 'is_active', 'nb_participants')
    list_filter = ('is_active', 'date_limite', 'entreprise')
    search_fields = ('titre', 'entreprise__company_name')
    
    inlines = [ParticipationInline] # Ajoute la liste des participants en bas de page

    def nb_participants(self, obj):
        return obj.participants.count()
    nb_participants.short_description = "Candidats"

@admin.register(ParticipationChallenge)
class ParticipationChallengeAdmin(admin.ModelAdmin):
    list_display = ('candidat', 'challenge', 'date_soumission', 'est_vainqueur', 'lien_fichier')
    list_filter = ('est_vainqueur', 'date_soumission')
    search_fields = ('candidat__full_name', 'challenge__titre')
    
    list_editable = ('est_vainqueur',) # Permet de déclarer un vainqueur directement depuis la liste !

    def lien_fichier(self, obj):
        if obj.fichier_rendu:
            return format_html('<a href="{}" target="_blank">Télécharger</a>', obj.fichier_rendu.url)
        return "-"
    lien_fichier.short_description = "Rendu"
    
from django.contrib import admin
from django.utils.html import format_html
from .models import EtudiantTalent, Competence

# Gestion des Étudiants Talents
@admin.register(EtudiantTalent)
class EtudiantTalentAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste
    list_display = ('apercu_photo', 'noms_prenoms', 'filiere', 'moyenne_generale', 'telephone', 'adresse_email')
    
    # Liens cliquables pour éditer
    list_display_links = ('apercu_photo', 'noms_prenoms')
    
    # Filtres sur la droite
    list_filter = ('filiere',)
    
    # Barre de recherche (Cherche par nom, email ou filière)
    search_fields = ('noms_prenoms', 'adresse_email', 'filiere', 'telephone')
    
    # Interface améliorée pour sélectionner les compétences (boite gauche/droite)
    filter_horizontal = ('competences',)
    
    # Ordre par défaut (Les meilleures moyennes en haut)
    ordering = ('-moyenne_generale',)
    
    # Pagination
    list_per_page = 20

    # Fonction pour afficher la petite photo ronde dans l'admin
    def apercu_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%; object-fit:cover; border: 2px solid #ccc;" />',
                obj.photo.url
            )
        return format_html('<span style="color: #ccc;">No IMG</span>')
    
    apercu_photo.short_description = "Photo"