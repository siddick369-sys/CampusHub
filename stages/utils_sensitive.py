# stages/utils_sensitive.py (ou autre)

import re

PHONE_REGEX = re.compile(r"\b6\d{8}\b")  # ex : 691234567
EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
WHATSAPP_REGEX = re.compile(
    r"(wa\.me/|whatsapp\.com/send)", re.IGNORECASE
)
SOCIAL_REGEX = re.compile(
    r"(facebook\.com|instagram\.com|tiktok\.com|snapchat\.com|twitter\.com|x\.com|telegram\.me|t\.me)",
    re.IGNORECASE,
)


def contains_sensitive_info(text: str) -> bool:
    """
    Renvoie True si le texte contient : numéro, email, lien WhatsApp
    ou réseaux sociaux.
    """
    if not text:
        return False

    patterns = [PHONE_REGEX, EMAIL_REGEX, WHATSAPP_REGEX, SOCIAL_REGEX]
    for p in patterns:
        if p.search(text):
            return True
    return False