from django.core.exceptions import ValidationError

def valider_taille_fichier_5mo(value):
    """
    Vérifie que le fichier ne dépasse pas 5 Mo.
    """
    limit_mb = 5
    limit_bytes = limit_mb * 1024 * 1024
    
    if value.size > limit_bytes:
        raise ValidationError(f"Le fichier est trop volumineux. Taille max : {limit_mb} Mo.")

def valider_taille_image_2mo(value):
    """
    Limite spécifique pour les images (ex: 2 Mo).
    """
    limit_mb = 2
    limit_bytes = limit_mb * 1024 * 1024
    
    if value.size > limit_bytes:
        raise ValidationError(f"L'image est trop lourde. Taille max : {limit_mb} Mo.")
