import os
from django import forms
from django.conf import settings
from .models import Application, StageOffer, StudentDocument

from .utils_files import validate_uploaded_file


class StageOfferForm(forms.ModelForm):
    application_deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type':'date','class':'form-control'}),
        input_formats=['%Y-%m-%d'],
    )
    class Meta:
        model = StageOffer
        exclude = (
            'company',
            'company_name_snapshot',
            'slug',
            'views_count',
            'applications_count',
            'created_at',
            'updated_at',
            
        )
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'responsibilities': forms.Textarea(attrs={'rows': 3}),
            'benefits': forms.Textarea(attrs={'rows': 3}),
            'skills_required': forms.Textarea(attrs={'rows': 3}),
            'skills_nice_to_have': forms.Textarea(attrs={'rows': 3}),
            'soft_skills_required': forms.Textarea(attrs={'rows': 3}),
            
        }

class ApplicationForm(forms.ModelForm):
    cv = forms.ModelChoiceField(
        queryset=StudentDocument.objects.none(),
        required=False,
        label="CV à utiliser"
    )

    class Meta:
        model = Application
        fields = ['cv', 'motivation_letter']
        widgets = {
            'motivation_letter': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields['cv'].queryset = StudentDocument.objects.filter(
                user=user,
                doc_type="cv"
            )
        
from django import forms
from .models import StudentDocument


class StudentDocumentForm(forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ["file", "title", "doc_type", "language", "description", "is_default_cv", "is_public"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.user = user
    def clean_file(self):
        f = self.cleaned_data.get("file")

        if not f:
            raise forms.ValidationError("Merci de choisir un fichier.")

        # 🔹 Taille max
        max_size = getattr(settings, "MAX_STUDENT_DOC_SIZE", 5 * 1024 * 1024)
        if f.size > max_size:
            size_mb = max_size / (1024 * 1024)
            raise forms.ValidationError(
                f"Fichier trop lourd. Taille max : {size_mb:.1f} Mo."
            )

        # 🔹 Extension
        ext = os.path.splitext(f.name)[1].lower().lstrip(".")
        allowed_exts = getattr(
            settings,
            "ALLOWED_STUDENT_DOC_EXTS",
            ["pdf", "doc", "docx", "odt", "png", "jpg", "jpeg"],
        )
        if ext not in allowed_exts:
            raise forms.ValidationError(
                "Ce type de fichier n'est pas autorisé. "
                f"Formats acceptés : {', '.join(allowed_exts)}."
            )

        return f

    def clean(self):
        """
        Limite le nombre total de documents pour un étudiant,
        pour éviter que quelqu’un uploade 500 fichiers.
        """
        cleaned = super().clean()
        cleaned_data = super().clean()
        doc_type = cleaned_data.get("doc_type")
        is_default_cv = cleaned_data.get("is_default_cv")

        # Si ce document est marqué comme CV par défaut
        if is_default_cv and doc_type != "cv":
            self.add_error("is_default_cv", "Seuls les documents de type CV peuvent être marqués comme CV par défaut.")

            return cleaned_data


        user = self.user
        if not user or not getattr(user, "id", None):
            return cleaned

        max_docs = getattr(settings, "MAX_STUDENT_DOCS_PER_USER", 50)
        current_count = StudentDocument.objects.filter(user=user).count()

        # Si c’est un nouveau document (pas une édition)
        if not self.instance.pk and current_count >= max_docs:
            raise forms.ValidationError(
                f"Tu as déjà atteint la limite de {max_docs} documents. "
                "Supprime d’anciens fichiers avant d’en ajouter de nouveaux."
            )

        return cleaned
    
    



        
    def save(self, commit=True):
        
        instance = super().save(commit=False)
        if self.user is not None and not instance.pk:
            instance.user = self.user

        # Si ce document est un CV par défaut, désactiver les autres
        if instance.doc_type == "cv" and instance.is_default_cv:
            StudentDocument.objects.filter(
                user=instance.user,
                doc_type="cv",
                is_default_cv=True
            ).update(is_default_cv=False)

        if commit:
            instance.save()
        return instance
    
    
    
from django import forms
from .models import StageReview
import re
from django import forms
from django.core.exceptions import ValidationError
import re
from django import forms
from django.core.exceptions import ValidationError
from .models import StageReview

class StageReviewForm(forms.ModelForm):
    class Meta:
        model = StageReview
        fields = ['rating', 'comment']
        widgets = {
            # On utilise HiddenInput car le système d'étoiles en JS remplira cette valeur
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={
                'class': 'form-control rounded-4 p-3',
                'rows': 5,
                'placeholder': 'Décrivez les missions, l\'ambiance et ce que vous avez appris...',
                'style': 'background-color: #f8fafc; border: 1px solid #e2e8f0;'
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating or rating < 1 or rating > 5:
            raise ValidationError("Veuillez sélectionner une note entre 1 et 5 étoiles.")
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        
        if not comment:
            return comment

        # 1. Protection contre le "Gibberish" (ex: jzjksuxvdb)
        # Bloque les suites de 5 consonnes ou plus sans voyelle/espace
        if re.search(r'[^aeiouyáàâäéèêëíìîïóòôöúùûü\s]{5,}', comment, re.IGNORECASE):
            raise ValidationError("Votre commentaire contient des mots qui semblent incohérents.")

        # 2. Protection contre les répétitions excessives (ex: nul nul nul)
        if re.search(r'(\b\w+\b)( \1){2,}', comment, re.IGNORECASE):
            raise ValidationError("Merci d'éviter les répétitions inutiles de mots.")

        # 3. Protection contre les caractères répétés (ex: aaaaaaaaaa)
        if re.search(r'(.)\1{4,}', comment):
            raise ValidationError("Évitez de répéter excessivement le même caractère.")
        

        useless_words = ['bonjour', 'allons', 'test', 'ok', 'ca marche', 'merci', 'super']
        if comment.lower().strip() in useless_words or len(comment.split()) < 3:
            raise ValidationError("Votre avis est trop court ou peu instructif pour la communauté.")


        # 4. Longueur minimale pour un avis utile
        if len(comment.strip()) < 15:
            raise ValidationError("Votre avis est trop court. Merci de détailler un peu plus votre expérience (min. 15 caractères).")

        return comment
