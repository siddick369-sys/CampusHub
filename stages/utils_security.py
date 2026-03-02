import hashlib

def build_request_fingerprint(request):
    """
    Construit une empreinte (hash) à partir de l'IP et du user-agent.
    Ce n'est pas parfait, mais ça suffit pour limiter les abus simples.
    """
    ip = request.META.get("REMOTE_ADDR", "") or ""
    ua = request.META.get("HTTP_USER_AGENT", "") or ""

    raw = f"{ip}|{ua}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()



# stages/utils_security.py

import mimetypes

from django.utils import timezone

from .utils_sensitive import contains_sensitive_info  # ta fonction texte déjà existante

MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024  # 4 Mo

ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif",
    ".pdf", ".txt", ".doc", ".docx",
}

def is_too_big(uploaded_file):
    """
    Vérifie si le fichier dépasse 4 Mo.
    """
    size = getattr(uploaded_file, "size", 0) or 0
    return size > MAX_ATTACHMENT_SIZE_BYTES


def is_extension_allowed(uploaded_file):
    """
    Vérifie l'extension autorisée.
    """
    name = getattr(uploaded_file, "name", "") or ""
    name = name.lower()
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith(ext):
            return True
    return False


def extract_text_from_file(uploaded_file):
    """
    Extraction très simple de texte brut.

    - .txt : décodage direct
    - .pdf, .doc, .docx : ici on retourne une string vide par défaut,
      sauf si tu veux ajouter PyPDF2 / python-docx plus tard.
    """
    name = (getattr(uploaded_file, "name", "") or "").lower()

    try:
        if name.endswith(".txt"):
            data = uploaded_file.read()
            try:
                return data.decode("utf-8", errors="ignore")
            except AttributeError:
                # déjà str
                return str(data)
        # 👉 pour l’instant, on ne fait pas d’OCR ni de parsing avancé
        # tu pourras brancher un service externe plus tard ici.
        return ""
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


def scan_attachment_for_sensitive_info(uploaded_file):
    """
    Retourne True si le fichier semble contenir des infos sensibles.
    (basé sur extract_text_from_file + contains_sensitive_info)
    """

    text = extract_text_from_file(uploaded_file)
    if not text:
        # on ne sait pas extraire → on est prudents : on considère que
        # le texte est "neutre", le warning viendra du front + message général
        return False

    return contains_sensitive_info(text)


def detect_mime(uploaded_file):
    """
    Détecte un type MIME simple à partir du nom de fichier.
    """
    name = getattr(uploaded_file, "name", "") or ""
    mime, _ = mimetypes.guess_type(name)
    return mime or "application/octet-stream"