import re
import unicodedata

# Configuration : On peut choisir de bloquer les numéros de téléphone ou non
ALLOW_PHONE_IN_REVIEWS = False

# Liste étendue de mots interdits (Français & Anglais)
# Cette liste peut être enrichie au fil du temps.
BAD_WORDS = [
    # Insultes généralistes (Français)
    "connard", "connasse", "salope", "merde", "pute", "salopard", "encule", "sac a merde",
    "fiston de pute", "fdp", "ntm", "bordel", "abruti", "débile", "imbécile", "crever",
    "pauvre con", "con", "grosse merde", "tronche de cul", "creve", "crevé",
    
    # Discours de haine / Racisme / Homophobie (Patterns à bloquer absolument)
    "negre", "bougnoul", "sale noir", "gniakoué", "pd", "pédé", "tapette", "fiotte",
    "gouine", "nazi", "hitler", "antisémite", "raciste", "sale juif", "islamophobe",
    "fachiste", "facho", "terroriste", "djihad",
    
    # Sexisme / Harcèlement
    "viol", "violer", "nympho", "pute", "chienne", "grosse truie", "pedophile", "pedo",
    "porn", "porno", "sexe", "bitte", "teuch", "chatte", "couille", "zizi",
    
    # Anglais (Commun)
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "pussy", "faggot", "nigger",
    "slut", "whore", "cunt", "motherfucker", "kill yourself", "kys", "die",
    
    # Arnaques / Spam
    "arnaque", "scam", "argent facile", "gagner du cash", "click ici", "orange money",
    "mtn money", "paypal money", "escroc", "escroquerie", "fraude", "hacker", "hacking",
]

# Regex pour détecter les variantes simples (ex: s.a.l.o.p.e ou s_a_l_o_p_e)
# On crée un pattern qui autorise des caractères spéciaux entre les lettres
def build_regex_pattern(words):
    patterns = []
    for word in words:
        # Autorise des séparateurs optionnels entre chaque lettre
        pattern = r"\b" + r"[\s\.\-\_\*]*".join(list(word)) + r"\b"
        patterns.append(pattern)
    return re.compile("|".join(patterns), re.IGNORECASE | re.UNICODE)

PROFANITY_PATTERN = build_regex_pattern(BAD_WORDS)

# Regex pour les numéros de téléphone (Cameroun & International basique)
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[\s\-\.]?)?(\d{2,3}[\s\-\.]?){3}\d{2,3}")

def normalize_text(text: str) -> str:
    """
    Supprime les accents et convertit en minuscules pour faciliter la détection.
    """
    if not text:
        return ""
    text = text.lower()
    # Décomposition des caractères accentués
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Filtrage des marques d'accent (Mn = Mark, Nonspacing)
    return "".join([c for c in nfkd_form if not unicodedata.category(c).startswith('M')])

def validate_content_moderation(text: str):
    """
    Analyse le contenu du texte.
    Retourne (is_safe, error_message)
    """
    if not text:
        return True, None

    normalized = normalize_text(text)

    # 1. Vérification des mots interdits / Insultes
    if PROFANITY_PATTERN.search(normalized) or PROFANITY_PATTERN.search(text):
        return False, "Votre message contient des termes inappropriés, injurieux ou contraires à nos règles de communauté."

    # 2. Vérification des numéros de téléphone (si désactivé)
    if not ALLOW_PHONE_IN_REVIEWS:
        if PHONE_PATTERN.search(text):
            return False, "Pour votre sécurité, le partage de numéros de téléphone n'est pas autorisé dans les avis publics."

    return True, None
