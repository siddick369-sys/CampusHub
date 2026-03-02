import re
from typing import Dict, Any, Optional, Set

from django.utils.text import slugify

from orientation.models import OrientationResult
from .models import StageOffer
from accounts.models import Profile


def _normalize_tokens(text: str) -> Set[str]:
    """
    Transforme une chaîne en ensemble de mots normalisés :
      - minuscules
      - accents retirés (via slugify)
      - séparés par espaces, virgules, points-virgules...
    """
    if not text:
        return set()

    # Remplace les séparateurs par des espaces
    text = re.sub(r"[,\;/|\n]+", " ", text)
    # Supprime les doubles espaces
    text = re.sub(r"\s+", " ", text).strip().lower()

    tokens = set()
    for part in text.split(" "):
        part = part.strip()
        if not part:
            continue
        normalized = slugify(part)  # enlève accents, caractères spéciaux
        if normalized:
            tokens.add(normalized)
    return tokens


def compute_matching_score(user, offer: StageOffer) -> Dict[str, Any]:
    """
    Calcule un score de matching entre un étudiant (user) et une offre.
    Retourne un dict :
      {
        "score": 87,  # 0..100 (int)
        "skills_score": 32,
        "tracks_score": 25,
        "location_score": 20,
        "level_score": 10,
      }
    Si l'utilisateur n'est pas un étudiant, score = None.
    """
    profile: Optional[Profile] = getattr(user, "profile", None)
    if not profile or profile.role != "student":
        return {
            "score": None,
            "skills_score": 0,
            "tracks_score": 0,
            "location_score": 0,
            "level_score": 0,
        }

    # Poids
    WEIGHT_SKILLS = 40
    WEIGHT_TRACKS = 30
    WEIGHT_LOCATION = 20
    WEIGHT_LEVEL = 10

    # ------------------------------------------------------------------
    # 1) Compétences (skills_required vs profil + orientation)
    # ------------------------------------------------------------------
    required_skills = _normalize_tokens(offer.skills_required or "")

    student_fields = []
    if profile.student_field:
        student_fields.append(profile.student_field)
    if profile.bio:
        student_fields.append(profile.bio)

    student_skills = set()
    for txt in student_fields:
        student_skills |= _normalize_tokens(txt)

    # On peut aussi utiliser les filières d'orientation pour enrichir les "skills"
    last_orientation = (
        OrientationResult.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )
    if last_orientation:
        for track in last_orientation.suggested_tracks.all():
            student_skills |= _normalize_tokens(track.main_skills or "")

    if required_skills:
        overlap = required_skills & student_skills
        ratio = len(overlap) / len(required_skills)
        skills_score = int(ratio * WEIGHT_SKILLS)
    else:
        skills_score = int(WEIGHT_SKILLS * 0.5)  # si l'offre n'a pas détaillé les skills

    # ------------------------------------------------------------------
    # 2) Tracks / filière (related_tracks vs orientation / student_field)
    # ------------------------------------------------------------------
    tracks_score = 0
    offer_tracks = list(offer.related_tracks.all())
    if offer_tracks:
        track_names = [t.name for t in offer_tracks]
        track_tokens = set()
        for name in track_names:
            track_tokens |= _normalize_tokens(name)

        orientation_match = 0
        if last_orientation:
            # si au moins une des filières proposées est dans les tracks de l'offre
            suggested_ids = set(last_orientation.suggested_tracks.values_list("id", flat=True))
            offer_track_ids = set(t.id for t in offer_tracks)
            common = suggested_ids & offer_track_ids
            if common:
                orientation_match = 1

        field_match = 0
        if profile.student_field:
            field_tokens = _normalize_tokens(profile.student_field)
            if field_tokens & track_tokens:
                field_match = 1

        # on donne 30 points si au moins l’un des deux matche, 30 si les deux
        if orientation_match and field_match:
            tracks_score = WEIGHT_TRACKS
        elif orientation_match or field_match:
            tracks_score = int(WEIGHT_TRACKS * 0.7)
        else:
            tracks_score = 0
    else:
        # pas de tracks définis → neutre
        tracks_score = int(WEIGHT_TRACKS * 0.4)

    # ------------------------------------------------------------------
    # 3) Localisation (ville + pays)
    # ------------------------------------------------------------------
    location_score = 0
    if offer.location_country:
        if profile.country and profile.country.lower().strip() == offer.location_country.lower().strip():
            # Même pays
            location_score = int(WEIGHT_LOCATION * 0.6)

            if offer.location_city and profile.city:
                if profile.city.lower().strip() == offer.location_city.lower().strip():
                    # Même ville → meilleur match
                    location_score = WEIGHT_LOCATION
        else:
            # Pays différent
            location_score = 0
    else:
        # Pas de localisation → neutre
        location_score = int(WEIGHT_LOCATION * 0.5)

    # ------------------------------------------------------------------
    # 4) Niveau (student_level vs required_level)
    # ------------------------------------------------------------------
    level_score = 0
    if offer.required_level and profile.student_level:
        # Comparaison simple par texte
        req = offer.required_level.lower()
        stu = dict(Profile.LEVEL_CHOICES).get(profile.student_level, "").lower()

        if req in stu or stu in req:
            level_score = WEIGHT_LEVEL
        else:
            # si les niveaux semblent "proches"
            if "licence" in req and "master" in stu:
                level_score = int(WEIGHT_LEVEL * 0.7)
            elif "master" in req and "licence" in stu:
                level_score = int(WEIGHT_LEVEL * 0.4)
            else:
                level_score = int(WEIGHT_LEVEL * 0.3)
    else:
        # pas d'info → neutre
        level_score = int(WEIGHT_LEVEL * 0.5)

    total = skills_score + tracks_score + location_score + level_score
    # clamp 0..100
    total = max(0, min(100, total))

    return {
        "score": total,
        "skills_score": skills_score,
        "tracks_score": tracks_score,
        "location_score": location_score,
        "level_score": level_score,
    }