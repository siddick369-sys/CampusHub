# stages/utils_files.py
from django.core.exceptions import ValidationError

MAX_UPLOAD_MB = 10  # limite générale, par ex. 10 Mo
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}

import os

def validate_uploaded_file(f):
    # 1) Taille
    size_mb = f.size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise ValidationError(f"Le fichier est trop lourd ({size_mb:.1f} Mo). Max : {MAX_UPLOAD_MB} Mo.")

    # 2) Extension
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Type de fichier non autorisé. Formats acceptés : PDF, DOC, DOCX, PNG, JPG."
        )

    # 3) Content-type
    content_type = getattr(f, "content_type", "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Type de fichier non autorisé (content-type incorrect).")