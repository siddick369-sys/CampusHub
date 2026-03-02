from django import forms
from django.contrib.auth.models import User

from CampuHub.settings import ALLOWED_AVATAR_CONTENT_TYPES, ALLOWED_AVATAR_EXTENSIONS, MAX_AVATAR_SIZE_MB
from  stages.utils_files import validate_uploaded_file
from .models import Profile


from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.core.exceptions import ValidationError


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Mot de passe"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmer le mot de passe"
    )

    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        label="Vous êtes :"
    )

    full_name = forms.CharField(label="Nom complet", required=False)
    phone = forms.CharField(label="Téléphone", required=False)
    city = forms.CharField(label="Ville", required=False)
    country = forms.CharField(label="Pays", required=False)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'role',
            'full_name',
            'phone',
            'city',
            'country',
        ]
        

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        pwd2 = cleaned_data.get("password_confirm")

        if pwd and pwd2 and pwd != pwd2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        return cleaned_data    
    
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'full_name',
            'phone',
            'city',
            'country',
            'address',
            'date_of_birth',
            'bio',
            'avatar',

            # étudiant
            'student_school',
            'student_level',
            'student_field',

            # entreprise
            'company_name',
            'company_position',
            'company_website',
            'company_description',

            # prestataire (uniquement la disponibilité, PAS le flag global)
            'provider_title',
            'provider_category',
            'provider_experience_years',
            'provider_hourly_rate',
            'provider_is_available',
            'provider_unavailable_until',
            'provider_availability_notes',
            'chat_start_time',
            'chat_end_time',
            'chat_manual_enabled',
            "kyc_document",
            
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "is_service_provider" in self.fields:
            self.fields["is_service_provider"].label = "Je veux proposer des services"
            self.fields["is_service_provider"].help_text = (
                "Cochez cette case si vous souhaitez offrir des prestations (coiffure, "
                "ménage, cours, développement, etc.)."
            )
            self.fields["chat_manual_enabled"].label = "Activer le chat maintenant"
            self.fields["chat_manual_enabled"].help_text = "Permet d’être visible ou invisible manuellement."
            self.fields["chat_start_time"].label = "Heure de début du chat"
            self.fields["chat_end_time"].label = "Heure de fin du chat"


        # (optionnel) aide sur l'avatar
        if "avatar" in self.fields:
            self.fields["avatar"].help_text = (
                f"Formats autorisés : JPG, PNG, WEBP – "
                f"taille max {MAX_AVATAR_SIZE_MB} Mo."
            )

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar

        # 🔹 Taille max
        max_bytes = MAX_AVATAR_SIZE_MB * 1024 * 1024
        if avatar.size > max_bytes:
            raise ValidationError(
                f"Ton image est trop lourde ({avatar.size / (1024*1024):.2f} Mo). "
                f"Taille maximale : {MAX_AVATAR_SIZE_MB} Mo."
            )

        # 🔹 Type MIME
        content_type = getattr(avatar, "content_type", "").lower()
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise ValidationError(
                "Format d'image non supporté. Utilise une image JPG, PNG ou WEBP."
            )

        # 🔹 Extension fichier (double sécurité)
        import os
        ext = os.path.splitext(avatar.name)[1].lower()
        if ext not in ALLOWED_AVATAR_EXTENSIONS:
            raise forms.ValidationError(
                "Extension de fichier non autorisée. "
                "Utilise une image en .jpg, .jpeg, .png ou .webp."
            )

        return avatar
    

        # (Optionnel) si tu utilises CE form dans l’admin, on garde le label propre
        from django import forms
from .models import Profile

class VerificationCodeForm(forms.Form):
    email = forms.CharField(label="email")
    code = forms.CharField(label="Code de vérification", max_length=6)
    
    
from django import forms
from .models import CompanyVerificationRequest


class CompanyVerificationRequestForm(forms.ModelForm):
    class Meta:
        model = CompanyVerificationRequest
        fields = ["document", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "document": "Document officiel",
            "message": "Informations complémentaires",
        }
        
        
from django import forms
from .models import Profile

class ServiceEmailSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["service_email_as_provider", "service_email_as_client"]
        labels = {
            "service_email_as_provider": "Recevoir des emails quand on commande mes services",
            "service_email_as_client": "Recevoir des emails pour mes commandes et alertes de services",
        }