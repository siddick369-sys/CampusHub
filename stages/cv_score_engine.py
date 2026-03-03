"""
CV Score Engine — ATS Analysis & Optimization
==============================================
Analyse un CV et fournit un score ATS sur 100,
des suggestions d'amélioration et des mots-clés manquants.
"""
import re
from collections import Counter

# Verbes d'action forts (français)
ACTION_VERBS_FR = {
    'piloté', 'conçu', 'développé', 'implémenté', 'optimisé', 'géré', 'coordonné',
    'dirigé', 'analysé', 'lancé', 'créé', 'automatisé', 'réduit', 'augmenté',
    'amélioré', 'supervisé', 'élaboré', 'structuré', 'déployé', 'intégré',
    'formé', 'négocié', 'présenté', 'résolu', 'trié', 'mis en place',
    'conçu', 'réalisé', 'participé', 'contribué', 'administré', 'encadré',
    'accompagné', 'produit', 'livré', 'testé', 'validé', 'sécurisé',
    'modernisé', 'migré', 'refactorisé', 'documenté', 'configuré',
}

# Verbes d'action forts (anglais)
ACTION_VERBS_EN = {
    'led', 'designed', 'developed', 'implemented', 'optimized', 'managed',
    'coordinated', 'directed', 'analyzed', 'launched', 'created', 'automated',
    'reduced', 'increased', 'improved', 'supervised', 'built', 'structured',
    'deployed', 'integrated', 'trained', 'negotiated', 'presented', 'resolved',
    'delivered', 'tested', 'secured', 'modernized', 'migrated', 'refactored',
    'documented', 'configured', 'architected', 'mentored', 'streamlined',
}

ACTION_VERBS = ACTION_VERBS_FR | ACTION_VERBS_EN

# Mots-clés ATS courants par domaine
ATS_KEYWORDS = {
    'tech': [
        'python', 'django', 'javascript', 'react', 'docker', 'api', 'rest', 'git',
        'sql', 'postgresql', 'html', 'css', 'linux', 'agile', 'ci/cd', 'devops',
        'machine learning', 'typescript', 'node.js', 'cloud', 'aws', 'azure',
    ],
    'business': [
        'gestion de projet', 'analyse', 'stratégie', 'budget', 'kpi', 'reporting',
        'excel', 'powerpoint', 'crm', 'marketing', 'communication', 'négociation',
    ],
    'general': [
        'leadership', 'travail d\'équipe', 'communication', 'résolution de problèmes',
        'organisation', 'autonomie', 'adaptabilité', 'créativité', 'rigueur',
    ],
}


def score_cv(cv_profile):
    """
    Analyse un CVProfile et retourne un dict avec les scores et suggestions.
    
    Returns:
        dict: {
            'overall_score': int (0-100),
            'keyword_score': int (0-25),
            'action_verbs_score': int (0-25),
            'completeness_score': int (0-25),
            'formatting_score': int (0-25),
            'missing_keywords': list,
            'suggestions': list,
            'weak_descriptions': list,
        }
    """
    scores = {
        'keyword_score': 0,
        'action_verbs_score': 0,
        'completeness_score': 0,
        'formatting_score': 0,
        'missing_keywords': [],
        'suggestions': [],
        'weak_descriptions': [],
    }

    # 1. COMPLETENESS SCORE (0-25)
    completeness = 0
    checks = [
        (bool(cv_profile.first_name and cv_profile.last_name), "Ajoutez votre nom complet"),
        (bool(cv_profile.professional_title), "Ajoutez un titre professionnel"),
        (bool(cv_profile.email), "Ajoutez votre email"),
        (bool(cv_profile.phone), "Ajoutez votre numéro de téléphone"),
        (bool(cv_profile.summary and len(cv_profile.summary) > 50), "Rédigez un résumé professionnel d'au moins 50 caractères"),
        (cv_profile.experiences.exists(), "Ajoutez au moins une expérience professionnelle"),
        (cv_profile.educations.exists(), "Ajoutez au moins une formation"),
        (cv_profile.skills.count() >= 3, "Ajoutez au moins 3 compétences"),
        (cv_profile.languages.exists(), "Ajoutez au moins une langue"),
        (bool(cv_profile.city), "Ajoutez votre ville"),
    ]
    for passed, suggestion in checks:
        if passed:
            completeness += 2.5
        else:
            scores['suggestions'].append(suggestion)
    scores['completeness_score'] = int(completeness)

    # 2. ACTION VERBS SCORE (0-25)
    all_text = _collect_all_text(cv_profile)
    words = set(re.findall(r'\b\w+\b', all_text.lower()))
    verbs_found = words & ACTION_VERBS
    verb_ratio = len(verbs_found) / max(len(ACTION_VERBS) * 0.1, 1)
    scores['action_verbs_score'] = min(25, int(verb_ratio * 25))

    if len(verbs_found) < 3:
        scores['suggestions'].append(
            "Utilisez plus de verbes d'action (développé, conçu, optimisé, piloté...)"
        )

    # 3. KEYWORD SCORE (0-25)
    all_keywords = set()
    for category_keywords in ATS_KEYWORDS.values():
        all_keywords.update(k.lower() for k in category_keywords)

    text_lower = all_text.lower()
    found_keywords = {kw for kw in all_keywords if kw in text_lower}
    missing = list(all_keywords - found_keywords)[:10]
    scores['missing_keywords'] = missing

    kw_ratio = len(found_keywords) / max(len(all_keywords) * 0.15, 1)
    scores['keyword_score'] = min(25, int(kw_ratio * 25))

    # 4. FORMATTING SCORE (0-25)
    fmt_score = 0

    # Check experience descriptions length
    weak = []
    for exp in cv_profile.experiences.all():
        if exp.description and len(exp.description) < 30:
            weak.append(f"Description trop courte pour '{exp.job_title}'")
            fmt_score -= 2
        elif exp.description and len(exp.description) >= 80:
            fmt_score += 3
        if not exp.description:
            weak.append(f"Aucune description pour '{exp.job_title}'")
    scores['weak_descriptions'] = weak

    # Check summary length
    if cv_profile.summary:
        if 100 <= len(cv_profile.summary) <= 500:
            fmt_score += 5
        elif len(cv_profile.summary) > 500:
            scores['suggestions'].append("Raccourcissez votre résumé (max 500 caractères recommandé)")
            fmt_score += 2

    # Check photo
    if cv_profile.photo:
        fmt_score += 2

    # Check if professional links exist
    if cv_profile.linkedin_url:
        fmt_score += 3
    else:
        scores['suggestions'].append("Ajoutez votre profil LinkedIn pour plus de crédibilité")

    if cv_profile.github_url or cv_profile.portfolio_url:
        fmt_score += 3

    # Balance the score
    scores['formatting_score'] = max(0, min(25, fmt_score + 10))

    # OVERALL
    scores['overall_score'] = (
        scores['keyword_score'] +
        scores['action_verbs_score'] +
        scores['completeness_score'] +
        scores['formatting_score']
    )

    return scores


def score_cv_for_offer(cv_profile, offer_title, offer_description, offer_skills=""):
    """
    Score un CV par rapport à une offre de stage/emploi spécifique.
    Retourne le score de base + un score de matching avec l'offre.
    """
    base_scores = score_cv(cv_profile)

    # Extract keywords from the offer
    offer_text = f"{offer_title} {offer_description} {offer_skills}".lower()
    offer_words = set(re.findall(r'\b\w{3,}\b', offer_text))

    # Compare with CV content
    cv_text = _collect_all_text(cv_profile).lower()
    cv_words = set(re.findall(r'\b\w{3,}\b', cv_text))

    # Matching keywords
    common = offer_words & cv_words
    stopwords = {'les', 'des', 'une', 'pour', 'dans', 'avec', 'est', 'sont', 'par', 'sur', 'que', 'qui', 'pas', 'plus', 'mais', 'the', 'and', 'for', 'with'}
    common -= stopwords
    offer_words -= stopwords

    match_ratio = len(common) / max(len(offer_words), 1)

    base_scores['offer_match_score'] = min(100, int(match_ratio * 100))
    base_scores['offer_missing_keywords'] = list(offer_words - cv_words)[:15]

    if match_ratio < 0.3:
        base_scores['suggestions'].append(
            f"Votre CV ne contient que {int(match_ratio*100)}% des mots-clés de l'offre. "
            "Ajoutez des termes spécifiques mentionnés dans la description du poste."
        )

    return base_scores


def _collect_all_text(cv_profile):
    """Collecte tout le texte d'un CV pour analyse."""
    parts = [
        cv_profile.summary or '',
        cv_profile.professional_title or '',
    ]
    for exp in cv_profile.experiences.all():
        parts.extend([exp.job_title, exp.company_name, exp.description or ''])
    for edu in cv_profile.educations.all():
        parts.extend([edu.diploma, edu.institution, edu.description or ''])
    for skill in cv_profile.skills.all():
        parts.append(skill.name)
    for proj in cv_profile.projects.all():
        parts.extend([proj.title, proj.description or '', proj.technologies or ''])
    for cert in cv_profile.certifications.all():
        parts.append(cert.name)

    return ' '.join(parts)
