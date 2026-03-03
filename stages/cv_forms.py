"""
CV Generator Pro — Forms & FormSets
====================================
"""
from django import forms
from django.forms import inlineformset_factory
from .cv_models import (
    CVProfile, CVExperience, CVEducation, CVSkill,
    CVLanguage, CVProject, CVCertification, CVInterest,
)

# ------------------------------------------------------------------
# Shared form field attrs
# ------------------------------------------------------------------
_INPUT = {'class': 'form-control', 'autocomplete': 'off'}
_TEXT = {'class': 'form-control', 'rows': 3}
_SELECT = {'class': 'form-select'}
_CHECK = {'class': 'form-check-input'}


# ------------------------------------------------------------------
# MAIN CV PROFILE FORM
# ------------------------------------------------------------------
class CVProfileForm(forms.ModelForm):
    class Meta:
        model = CVProfile
        fields = [
            'title', 'first_name', 'last_name', 'professional_title',
            'email', 'phone', 'city', 'country',
            'linkedin_url', 'portfolio_url', 'github_url',
            'photo', 'summary',
            'primary_color', 'secondary_color', 'font_family',
            'photo_frame', 'skill_display',
        ]
        widgets = {
            'title': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Mon CV'}),
            'first_name': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Nom'}),
            'professional_title': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ex: Développeur Full-Stack'}),
            'email': forms.EmailInput(attrs={**_INPUT, 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={**_INPUT, 'placeholder': '+237 6XX XXX XXX'}),
            'city': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ville'}),
            'country': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Pays'}),
            'linkedin_url': forms.URLInput(attrs={**_INPUT, 'placeholder': 'https://linkedin.com/in/...'}),
            'portfolio_url': forms.URLInput(attrs={**_INPUT, 'placeholder': 'https://...'}),
            'github_url': forms.URLInput(attrs={**_INPUT, 'placeholder': 'https://github.com/...'}),
            'summary': forms.Textarea(attrs={**_TEXT, 'placeholder': 'Résumé professionnel...', 'rows': 4}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'font_family': forms.Select(attrs=_SELECT),
            'photo_frame': forms.Select(attrs=_SELECT),
            'skill_display': forms.Select(attrs=_SELECT),
        }


# ------------------------------------------------------------------
# REPEATABLE SECTION FORMS
# ------------------------------------------------------------------
class CVExperienceForm(forms.ModelForm):
    class Meta:
        model = CVExperience
        fields = ['job_title', 'company_name', 'location', 'start_date', 'end_date', 'is_current', 'description', 'order']
        widgets = {
            'job_title': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Intitulé du poste'}),
            'company_name': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Entreprise'}),
            'location': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ville, Pays'}),
            'start_date': forms.TextInput(attrs={**_INPUT, 'placeholder': 'MM/AAAA'}),
            'end_date': forms.TextInput(attrs={**_INPUT, 'placeholder': 'MM/AAAA (vide si en poste)'}),
            'is_current': forms.CheckboxInput(attrs=_CHECK),
            'description': forms.Textarea(attrs={**_TEXT, 'placeholder': 'Décrivez vos missions...'}),
            'order': forms.HiddenInput(),
        }


class CVEducationForm(forms.ModelForm):
    class Meta:
        model = CVEducation
        fields = ['diploma', 'institution', 'location', 'start_date', 'end_date', 'description', 'order']
        widgets = {
            'diploma': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Diplôme obtenu'}),
            'institution': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Établissement'}),
            'location': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ville, Pays'}),
            'start_date': forms.TextInput(attrs={**_INPUT, 'placeholder': 'MM/AAAA'}),
            'end_date': forms.TextInput(attrs={**_INPUT, 'placeholder': 'MM/AAAA'}),
            'description': forms.Textarea(attrs={**_TEXT, 'placeholder': 'Description (optionnel)', 'rows': 2}),
            'order': forms.HiddenInput(),
        }


class CVSkillForm(forms.ModelForm):
    class Meta:
        model = CVSkill
        fields = ['name', 'level', 'category', 'order']
        widgets = {
            'name': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ex: Python, Communication...'}),
            'level': forms.Select(attrs=_SELECT),
            'category': forms.Select(attrs=_SELECT),
            'order': forms.HiddenInput(),
        }


class CVLanguageForm(forms.ModelForm):
    class Meta:
        model = CVLanguage
        fields = ['language', 'level', 'order']
        widgets = {
            'language': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ex: Français'}),
            'level': forms.Select(attrs=_SELECT),
            'order': forms.HiddenInput(),
        }


class CVProjectForm(forms.ModelForm):
    class Meta:
        model = CVProject
        fields = ['title', 'description', 'url', 'technologies', 'order']
        widgets = {
            'title': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Nom du projet'}),
            'description': forms.Textarea(attrs={**_TEXT, 'placeholder': 'Description...', 'rows': 2}),
            'url': forms.URLInput(attrs={**_INPUT, 'placeholder': 'https://...'}),
            'technologies': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Django, React, Docker...'}),
            'order': forms.HiddenInput(),
        }


class CVCertificationForm(forms.ModelForm):
    class Meta:
        model = CVCertification
        fields = ['name', 'issuer', 'date', 'url', 'order']
        widgets = {
            'name': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Nom de la certification'}),
            'issuer': forms.TextInput(attrs={**_INPUT, 'placeholder': 'Organisme'}),
            'date': forms.TextInput(attrs={**_INPUT, 'placeholder': 'MM/AAAA'}),
            'url': forms.URLInput(attrs={**_INPUT, 'placeholder': 'Lien de vérification'}),
            'order': forms.HiddenInput(),
        }


class CVInterestForm(forms.ModelForm):
    class Meta:
        model = CVInterest
        fields = ['name', 'order']
        widgets = {
            'name': forms.TextInput(attrs={**_INPUT, 'placeholder': "Centre d'intérêt"}),
            'order': forms.HiddenInput(),
        }


# ------------------------------------------------------------------
# FORMSETS (inline, extra=1 for dynamic add)
# ------------------------------------------------------------------
CVExperienceFormSet = inlineformset_factory(
    CVProfile, CVExperience, form=CVExperienceForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)
CVEducationFormSet = inlineformset_factory(
    CVProfile, CVEducation, form=CVEducationForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)
CVSkillFormSet = inlineformset_factory(
    CVProfile, CVSkill, form=CVSkillForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)
CVLanguageFormSet = inlineformset_factory(
    CVProfile, CVLanguage, form=CVLanguageForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)
CVProjectFormSet = inlineformset_factory(
    CVProfile, CVProject, form=CVProjectForm,
    extra=0, can_delete=True, min_num=0, validate_min=False,
)
CVCertificationFormSet = inlineformset_factory(
    CVProfile, CVCertification, form=CVCertificationForm,
    extra=0, can_delete=True, min_num=0, validate_min=False,
)
CVInterestFormSet = inlineformset_factory(
    CVProfile, CVInterest, form=CVInterestForm,
    extra=0, can_delete=True, min_num=0, validate_min=False,
)
