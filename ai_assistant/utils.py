import re
import unicodedata
import hashlib

def normalize_question(text):
    """
    Normalise la question de l'utilisateur pour le cache :
    - Mise en minuscule
    - Suppression des accents
    - Suppression de la ponctuation inutile
    - Suppression des espaces en trop
    """
    if not text:
        return ""
    
    # Mise en minuscule
    text = text.lower().strip()
    
    # Normalisation Unicode (NFKD) et suppression des accents
    text = "".join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )
    
    # Suppression de la ponctuation (garde seulement alphanumérique et espaces)
    text = re.sub(r'[^\w\s]', '', text)
    
    # Suppression des espaces multiples
    text = " ".join(text.split())
    
    return text

def generate_question_hash(normalized_text):
    """
    Génère un hash SHA-256 pour une recherche rapide en base.
    """
    return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()

# Note: On pourra ajouter ici une fonction pour charger un modèle de Sentence-Transformers
# si l'utilisateur souhaite une détection de similarité sémantique avancée.
