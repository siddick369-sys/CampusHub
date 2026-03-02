from django import forms
from .models import ProjetInnovation, ParticipationChallenge, ChallengeEntreprise, Competence
from django import forms
from .models import ProjetInnovation

from django import forms
from .models import ProjetInnovation

class ProjetForm(forms.ModelForm):
    # Champ spécial pour l'affichage en mode "Interrupteur" (Toggle)
    est_en_recrutement = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox toggle-switch'}),
        label="Je cherche activement à agrandir l'équipe"
    )

    class Meta:
        model = ProjetInnovation
        fields = [
            'titre', 'secteur', 'stade', 
            'description_courte', 'description_complete', 
            'image_couverture', 'video_demo', 'dossier_projet', 
            'est_en_recrutement', 'competences_recherchees', # Nouveaux champs recrutement
            'cherche_financement', 'besoins',
            'lien_whatsapp', 'lien_instagram', 'lien_linkedin', 'site_web' # Nouveaux liens
        ]
        
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Ex: Jus de Gingembre Bio, Application de Tontine...'
            }),
            'secteur': forms.Select(attrs={'class': 'form-select'}),
            'stade': forms.Select(attrs={'class': 'form-select'}),
            'description_courte': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Expliquez votre projet en une seule phrase percutante.'
            }),
            'description_complete': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 6,
                'placeholder': 'Racontez votre histoire : \n- Quel problème résolvez-vous ?\n- Quelle est votre solution ?\n- Qui sont vos clients ?'
            }),
            'besoins': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3,
                'placeholder': 'Ex: Je cherche 50.000 FCFA pour acheter des bouteilles, ou un graphiste pour mon logo...'
            }),
            'image_couverture': forms.FileInput(attrs={'class': 'form-input-file', 'accept': 'image/*'}),
            'dossier_projet': forms.FileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.ppt,.pptx'}),
            'video_demo': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://youtube.com/...'}),
            
            # --- WIDGETS POUR LES NOUVEAUX LIENS ---
            'lien_whatsapp': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://wa.me/2376...'}),
            'lien_instagram': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://instagram.com/mon_projet'}),
            'lien_linkedin': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/...'}),
            'site_web': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://mon-portfolio.com'}),
            
            'competences_recherchees': forms.SelectMultiple(attrs={
                'class':'form-select select-choices'
                }),
            'cherche_financement': forms.CheckboxInput(attrs={'class': 'form-checkbox toggle-switch'}),
        }
class ParticipationForm(forms.ModelForm):
    class Meta:
        model = ParticipationChallenge
        fields = ['fichier_rendu', 'description_solution', 'lien_externe']
        widgets = {
            'description_solution': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Expliquez brièvement votre approche...'}),
            'lien_externe': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            # --- AJOUT ICI : Filtre Fichiers ---
            'fichier_rendu': forms.FileInput(attrs={
                'class': 'form-input-file', 
                'accept': '.pdf,.zip,.rar,.doc,.docx'
            }),
        }
from django import forms
from .models import ChallengeEntreprise
from django import forms
from .models import ChallengeEntreprise, Competence 

class ChallengeForm(forms.ModelForm):
    # ✅ CORRECTION : On définit le champ ICI, en dehors de Meta
    competences_cibles = forms.ModelMultipleChoiceField(
        queryset=Competence.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}), # C'est ce widget qui permettra le Select2
        label="Cochez les profils d'étudiants que vous visez :"
    )

    class Meta:
        model = ChallengeEntreprise
        fields = [
            'titre', 'secteur', 'type_challenge', 
            'description', 'cahier_des_charges', 'image_illustration',
            'format_rendu', 'competences_cibles',
            'recompense', 'date_limite'
        ]
        
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Ex: Création du Logo pour la Boulangerie X, Stratégie Marketing pour Y...'
            }),
            
            'secteur': forms.Select(attrs={'class': 'form-select'}),
            'type_challenge': forms.Select(attrs={'class': 'form-select'}),
            'format_rendu': forms.Select(attrs={'class': 'form-select'}),
            
            'description': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 6,
                'placeholder': 'Contexte : Nous lançons un nouveau produit...\nObjectif : Proposez un slogan et une affiche...\nCritères : Originalité, respect des couleurs...'
            }),
            
            'recompense': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Ex: Prime de 100.000 FCFA, Stage, Bon d\'achat...'
            }),
            
            'date_limite': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            
            'cahier_des_charges': forms.FileInput(attrs={'class': 'form-input-file', 'accept': '.pdf,.doc,.docx'}),
            'image_illustration': forms.FileInput(attrs={'class': 'form-input-file', 'accept': 'image/*'}),
            
            # ❌ J'ai supprimé la ligne 'competences_cibles' ici car elle est gérée au-dessus
        }

    # Le __init__ n'est plus nécessaire pour le label car on l'a défini plus haut,
    # mais tu peux le garder si tu as d'autres logiques.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# incubateur/forms.py
from .models import ProjetUpdate

class ProjetUpdateForm(forms.ModelForm):
    class Meta:
        model = ProjetUpdate
        fields = ['titre', 'contenu', 'image']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: On a fini le prototype !'}),
            'contenu': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Racontez ce qui s\'est passé...'}),
            'image': forms.FileInput(attrs={'class': 'form-input-file'}),
        }
        
        
        
from django import forms
from .models import InterviewSession

class InterviewSetupForm(forms.ModelForm):
    class Meta:
        model = InterviewSession
        fields = ['target_role', 'difficulty']
        widgets = {
            'target_role': forms.TextInput(attrs={
                'class': 'input-neon', 
                'placeholder': 'Ex: UX Designer, Chef de Projet...'
            }),
            'difficulty': forms.Select(attrs={'class': 'input-neon'}),
        }
        labels = {
            'target_role': 'Poste visé',
            'difficulty': 'Niveau de difficulté'
        }