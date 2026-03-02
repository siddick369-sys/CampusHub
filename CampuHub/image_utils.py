import sys
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

def optimize_image(image_field, max_width=1200, max_height=1200, quality=75):
    """
    Redimensionne et compresse une image pour optimiser le stockage et la vitesse d'upload.
    Retourne une instance de InMemoryUploadedFile si l'image a été modifiée, sinon l'original.
    """
    if not image_field:
        return image_field

    try:
        # Ouvrir l'image avec Pillow
        img = Image.open(image_field)
        
        # Conserver le format original si possible, sinon JPEG par défaut
        img_format = img.format if img.format else 'JPEG'
        
        # Redimensionnement proportionnel si l'image dépasse les dimensions max
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Préparation de l'enregistrement
        output = BytesIO()
        
        # Conversion en RGB si nécessaire (pour JPEG)
        if img.mode in ('RGBA', 'P') and img_format == 'JPEG':
            img = img.convert('RGB')
            
        # Sauvegarde compressée
        img.save(output, format=img_format, quality=quality, optimize=True)
        output.seek(0)
        
        # Création du nouvel objet file pour Django
        optimized_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_field.name.split('.')[0]}.{img_format.lower()}",
            f"image/{img_format.lower()}",
            sys.getsizeof(output),
            None
        )
        
        return optimized_file
        
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation de l'image {image_field.name}: {e}")
        return image_field
