from django import forms
from django.utils.text import slugify
from .models import ServiceOffer, ServiceMedia, ServiceFAQ, ServiceCategory, ServicePackage, ServiceTag

from django import forms
from django.utils.text import slugify
from .models import ServiceOffer, ServiceMedia, ServiceOrder


class MultipleFileInput(forms.ClearableFileInput):
    """
    Widget qui autorise l'upload de plusieurs fichiers.
    """
    allow_multiple_selected = True

from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from .models import ServiceOffer, ServiceMedia, ServiceTag

# --- 1. Widget pour le HTML (multiple) ---
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# --- 2. Champ personnalisé pour gérer la LISTE de fichiers (Crucial) ---
class MultipleFileField(forms.FileField):
    def to_python(self, data):
        if not data:
            return None
        return data

    def clean(self, data, initial=None):
        # On évite que Django valide "required" sur une liste vide ici,
        # on gérera ça manuellement ou via clean_media_files
        if not data and self.required:
            raise ValidationError(self.error_messages['required'])
        return data

class ServiceOfferForm(forms.ModelForm):
    # Utilisation de notre champ personnalisé
    media_files = MultipleFileField(
        required=False, 
        widget=MultipleFileInput(attrs={'multiple': True}), 
        label="Galerie (Images uniquement)",
        help_text="Format: JPG, PNG, WEBP. Taille max: 5Mo par fichier."
    )
    
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "tagify-input",
            "placeholder": "Entrez vos mots-clés…"
        }),
        label="Étiquettes (tags)"
    )
    
    video_urls = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3, 
            "placeholder": "Collez ici une ou plusieurs URLs YouTube décrivant votre prestation"
        })
    )

    class Meta:
        model = ServiceOffer
        fields = [
            "title",
            "short_description",
            "description",
            "category",
            "tags",
            "price_min",
            "price_max",
            "currency",
            "is_price_negotiable",
            "delivery_time_min_days",
            "delivery_time_max_days",
            "revisions_included",
            "visibility",
            "status",
            "is_featured",
            "single_active_order",
            "allow_urgent",
            # Ajoute ici d'autres champs si ton modèle en a (ex: urgent_extra_percent)
        ]

        widgets = {
            "tags": forms.SelectMultiple(attrs={'id': 'id_tags', 'class': 'form-control'}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.Textarea(attrs={"rows": 3}),
        }

        labels = {
            "title": "Titre du service",
            "short_description": "Brève description",
            "description": "Description détaillée",
            "category": "Catégorie",
            "tags": "Étiquettes (tags)",
            "price_min": "Prix minimum",
            "price_max": "Prix maximum",
            "currency": "Devise",
            "is_price_negotiable": "Prix négociable ?",
            "delivery_time_min_days": "Délai minimum (jours)",
            "delivery_time_max_days": "Délai maximum (jours)",
            "revisions_included": "Révisions incluses",
            "visibility": "Visibilité",
            "status": "Statut",
            "is_featured": "Mettre en avant",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- SÉCURITÉ : Forcer les champs optionnels ---
        # Tags est optionnel car on utilise tags_input
        if 'tags' in self.fields:
            self.fields["tags"].required = False
            
        # media_files est optionnel (on ne veut pas bloquer si pas d'image)
        self.fields["media_files"].required = False

        # Labels spécifiques
        if 'single_active_order' in self.fields:
            self.fields["single_active_order"].label = "Une seule commande à la fois"
            self.fields["single_active_order"].help_text = (
                "Si coché, le service sera indisponible tant qu'une commande en cours existe."
            )

    # ==============================
    # 🛡️ VALIDATION DES FICHIERS (IMAGES & TAILLE)
    # ==============================
    def clean_media_files(self):
        """
        Vérifie que chaque fichier est une image et respecte la taille limite.
        """
        # On récupère la liste brute des fichiers
        files = self.files.getlist('media_files')
        
        # Configuration
        MAX_SIZE_MB = 2
        MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
        ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']

        cleaned_files = []

        for f in files:
            # 1. Vérification Taille
            if f.size > MAX_SIZE_BYTES:
                raise ValidationError(f"Le fichier '{f.name}' est trop volumineux (Max {MAX_SIZE_MB}Mo).")
            
            # 2. Vérification Type (MIME)
            # On utilise content_type (envoyé par le navigateur)
            # Pour plus de sécu, on pourrait utiliser python-magic, mais content_type suffit souvent pour l'UX
            content_type = getattr(f, 'content_type', '').lower()
            if content_type not in ALLOWED_TYPES:
                raise ValidationError(f"Le fichier '{f.name}' n'est pas une image valide (JPG, PNG, WEBP autorisés).")
            
            cleaned_files.append(f)

        return cleaned_files

    # ==============================
    # 🔍 VALIDATIONS LOGIQUES
    # ==============================
    def clean(self):
        cleaned_data = super().clean()
        price_min = cleaned_data.get("price_min")
        price_max = cleaned_data.get("price_max")

        if price_min and price_max and price_min > price_max:
            raise ValidationError("Le prix minimum ne peut pas être supérieur au prix maximum.")

        dmin = cleaned_data.get("delivery_time_min_days")
        dmax = cleaned_data.get("delivery_time_max_days")

        if dmin and dmax and dmin > dmax:
            raise ValidationError("Le délai minimum ne peut pas être supérieur au délai maximum.")
        
        return cleaned_data

    # ==============================
    # 💾 SAUVEGARDE
    # ==============================
    def save(self, provider=None, commit=True):
        instance = super().save(commit=False)

        # Assigner le prestataire
        if provider:
            instance.provider = provider

        # Générer le slug
        if not instance.slug:
            instance.slug = slugify(instance.title)

        if commit:
            instance.save()
            self.save_m2m() # Important pour les tags ManyToMany du modèle

            # --- GESTION DES FICHIERS ---
            # On utilise les fichiers nettoyés ou bruts
            files_to_save = self.cleaned_data.get('media_files') or []
            
            # Si cleaned_data est vide mais que self.files existe (cas rare), on fallback
            if not files_to_save and self.files:
                files_to_save = self.files.getlist('media_files')

            for f in files_to_save:
                if not f: continue
                
                # On est sûr que c'est une image grâce au clean_media_files
                ServiceMedia.objects.create(
                    service=instance, 
                    media_type="image", 
                    image=f
                )

        return instance

    # ==============================
    # 🔧 SAUVEGARDE AVANCÉE
    # ==============================
    

from django import forms
from .models import ServiceReview

class ServiceReviewForm(forms.ModelForm):
    class Meta:
        model = ServiceReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 5,
            }),
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Décrivez votre expérience avec ce prestataire..."
            }),
        }
        labels = {
            "rating": "Note (1 à 5)",
            "comment": "Votre avis (optionnel)",
        }
    
from django import forms
from .models import ServiceReview, ServiceOrderReport  # + ServiceReview si pas déjà


class ServiceOrderReportForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderReport
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Explique clairement le problème (ex : le prestataire n'est pas venu, insulte, arnaque, etc.)"
            })
        }
        labels = {
            "reason": "Raison du signalement",
        }
    
from django import forms
from .models import ServiceOrder


class ServiceOrderStatusForm(forms.Form):
    """
    Form utilisé par le prestataire pour changer le statut d'une commande.
    On limite les choix aux transitions autorisées depuis le statut actuel.
    """
    new_status = forms.ChoiceField(label="Nouveau statut")
    reason = forms.CharField(
        label="Commentaire (optionnel)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, order: ServiceOrder = None, **kwargs):
        self.order = order
        super().__init__(*args, **kwargs)

        # Par défaut, aucun choix si pas d'order
        choices = []

        if order is not None:
            # Même mapping que dans ServiceOrder.change_status
            allowed_transitions = {
                "pending": {"accepted", "cancelled"},
                "accepted": {"in_progress", "cancelled"},
                "in_progress": {"delivered", "cancelled"},
                "delivered": {"completed", "cancelled"},
                "completed": set(),
                "cancelled": set(),
            }

            allowed = allowed_transitions.get(order.status, set())
            # Filtrer les STATUS_CHOICES
            choices = [
                (value, label)
                for value, label in ServiceOrder.STATUS_CHOICES
                if value in allowed
            ]

        self.fields["new_status"].choices = choices

    def clean_new_status(self):
        new_status = self.cleaned_data.get("new_status")
        if not new_status:
            raise forms.ValidationError("Veuillez choisir un statut.")
        return new_status
from django import forms
from django.utils import timezone

from .models import ServiceOffer, ServiceOrder


class ServiceOrderForm(forms.ModelForm):
    """
    Formulaire pour créer une commande de service côté client.
    L'utilisateur choisit :
      - le prix (dans la fourchette du service)
      - une petite description / brief
    """

    class Meta:
        model = ServiceOrder
        fields = ["agreed_price", "description_brief"]

        labels = {
            "agreed_price": "Prix proposé",
            "description_brief": "Description de votre besoin",
        }

        widgets = {
            "description_brief": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, service: ServiceOffer = None, **kwargs):
        """
        On passe le service au formulaire pour pouvoir valider le prix.
        """
        self.service = service
        super().__init__(*args, **kwargs)

        # Optionnel : afficher un help_text avec la fourchette
        if self.service:
            self.fields["agreed_price"].help_text = (
                f"Entre {self.service.price_min} et {self.service.price_max} {self.service.currency}."
            )

    def clean_agreed_price(self):
        price = self.cleaned_data.get("agreed_price")
        service = self.service

        if service:
            # Contrôle sur la fourchette
            if price is None:
                raise forms.ValidationError("Veuillez indiquer un prix.")
            if price < service.price_min or price > service.price_max:
                raise forms.ValidationError(
                    f"Le prix doit être compris entre {service.price_min} et {service.price_max} {service.currency}."
                )
        else:
            # Au cas où, si pour une raison bizarre le service n'est pas passé
            if price is None or price <= 0:
                raise forms.ValidationError("Le prix proposé doit être positif.")

        return price

    def save(self, client, service: ServiceOffer, commit=True):
        """
        Crée une ServiceOrder proprement :
          - remplit client / provider
          - fait les snapshots (titre, username)
          - copie la devise, le nombre de révisions, etc.
          - calcule une due_date de base
        """
        order: ServiceOrder = super().save(commit=False)

        order.client = client
        order.service = service
        order.provider = service.provider

        # Snapshots
        order.service_title_snapshot = service.title
        order.provider_username_snapshot = service.provider.username

        # Copie de la devise & des révisions depuis le service
        order.currency = service.currency
        order.max_revisions = service.revisions_included

        # Statut de départ
        order.status = "pending"
        order.status_changed_at = timezone.now()

        # Due date (ici on prend delivery_time_max_days, tu peux adapter)
        if service.delivery_time_max_days:
            order.due_date = timezone.now() + timezone.timedelta(days=service.delivery_time_max_days)

        if commit:
            order.save()

        return order
    
    
from django import forms
from .models import ServiceOrder


class ServiceOrderStatusForm(forms.Form):
    """
    Form utilisé par le prestataire pour changer le statut d'une commande.
    On limite les choix aux transitions autorisées depuis le statut actuel.
    """
    new_status = forms.ChoiceField(label="Nouveau statut")
    reason = forms.CharField(
        label="Commentaire (optionnel)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, order: ServiceOrder = None, **kwargs):
        self.order = order
        super().__init__(*args, **kwargs)

        # Par défaut, aucun choix si pas d'order
        choices = []

        if order is not None:
            # Même mapping que dans ServiceOrder.change_status
            allowed_transitions = {
                "pending": {"accepted", "cancelled"},
                "accepted": {"in_progress", "cancelled"},
                "in_progress": {"delivered", "cancelled"},
                "delivered": {"completed", "cancelled"},
                "completed": set(),
                "cancelled": set(),
            }

            allowed = allowed_transitions.get(order.status, set())
            # Filtrer les STATUS_CHOICES
            choices = [
                (value, label)
                for value, label in ServiceOrder.STATUS_CHOICES
                if value in allowed
            ]

        self.fields["new_status"].choices = choices

    def clean_new_status(self):
        new_status = self.cleaned_data.get("new_status")
        if not new_status:
            raise forms.ValidationError("Veuillez choisir un statut.")
        return new_status
    
    
    
from django import forms
from .models import ServiceOrder


class ServiceOrderClientActionForm(forms.Form):
    """
    Formulaire pour le CLIENT d'une commande.
    Il peut :
      - marquer la commande comme 'completed'
      - demander l'annulation ('cancelled')
    selon le statut actuel.
    """
    ACTION_COMPLETE = "complete"
    ACTION_CANCEL = "cancel"

    ACTION_CHOICES = [
        (ACTION_COMPLETE, "Confirmer que le service est bien terminé"),
        (ACTION_CANCEL, "Demander l'annulation de la commande"),
    ]

    action = forms.ChoiceField(label="Que souhaitez-vous faire ?")
    reason = forms.CharField(
        label="Commentaire (optionnel, mais recommandé pour une annulation)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, order: ServiceOrder = None, **kwargs):
        self.order = order
        super().__init__(*args, **kwargs)

        choices = []
        if order is not None:
            # Si la commande est livrée → le client peut :
            #   - valider (completed)
            #   - demander l'annulation
            if order.status == "delivered":
                choices = self.ACTION_CHOICES

            # Si la commande est en cours mais pas livrée, il peut seulement annuler
            elif order.status in ("pending", "accepted", "in_progress"):
                choices = [
                    (self.ACTION_CANCEL, "Demander l'annulation de la commande"),
                ]

            # Si déjà 'completed' ou 'cancelled' → aucune action
            else:
                choices = []

        self.fields["action"].choices = choices

    def clean_action(self):
        action = self.cleaned_data.get("action")
        if not action:
            raise forms.ValidationError("Veuillez choisir une action.")
        # S'il n'y a pas d'action possible mais le client bricole le POST :
        if not self.fields["action"].choices:
            raise forms.ValidationError("Aucune action n'est possible pour cette commande.")
        return action

    def apply(self, actor):
        """
        Applique l'action choisie sur la commande :
          - 'complete'  -> status 'completed'
          - 'cancel'    -> status 'cancelled'
        Utilise ServiceOrder.change_status pour respecter les transitions
        et enregistrer l'historique.
        """
        if not self.order:
            return

        action = self.cleaned_data["action"]
        reason = self.cleaned_data.get("reason") or ""

        if action == self.ACTION_COMPLETE:
            # On demande à passer en 'completed'
            self.order.change_status("completed", actor=actor, reason=reason)

        elif action == self.ACTION_CANCEL:
            # On demande à passer en 'cancelled'
            self.order.change_status("cancelled", actor=actor, reason=reason)
            
            
class ServicePackageForm(forms.ModelForm):
    class Meta:
        model = ServicePackage
        # On ne garde QUE les champs présents dans ton modal
        fields = ["title", "description", "price", "delivery_time_days"]
        
# services/forms.py

from django import forms
from .models import ProviderTimeSlot

class ProviderTimeSlotForm(forms.ModelForm):
    class Meta:
        model = ProviderTimeSlot
        fields = [
            "weekday",
            "start_time",
            "end_time",
            "capacity",
            "service",
        ]