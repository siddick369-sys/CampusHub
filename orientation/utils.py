# orientation/utils.py
from django.db.models import Q
from .models import ChoiceTrackScore, Question, Track
from datetime import timedelta
from django.utils import timezone

def calculate_orientation_scores(quiz_answers):
    """
    Calcule les scores d'orientation basés sur les réponses du quiz.
    """
    track_scores = {}
    category_scores = {}

    for question_id, choice_id in quiz_answers.items():
        if not choice_id:
            continue

        cts_qs = ChoiceTrackScore.objects.filter(choice_id=choice_id)
        total_for_question = 0

        for cts in cts_qs:
            track_id = cts.track_id
            score = cts.score

            track_scores[track_id] = track_scores.get(track_id, 0) + score
            total_for_question += score

        if total_for_question > 0:
            try:
                question = Question.objects.get(id=question_id)
                cat = question.category
                category_scores[cat] = category_scores.get(cat, 0) + total_for_question
            except Question.DoesNotExist:
                pass

    return {
        'tracks': track_scores,
        'categories': category_scores
    }

def get_track_recommendation_priority(track_scores, max_recommendations=3):
    """
    Détermine les filières recommandées en priorité.
    """
    sorted_tracks = sorted(
        track_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return [track_id for track_id, score in sorted_tracks[:max_recommendations]]

def generate_personalized_comment(track_score_list, category_scores):
    """
    Génère un commentaire personnalisé basé sur les résultats.
    """
    if not track_score_list:
        return "Vos centres d'intérêt sont variés. Explorez plusieurs filières pour trouver celle qui vous correspond le mieux."

    top_track, top_score = track_score_list[0]
    
    dominant_categories = sorted(
        category_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:2]
    
    dominant_category_names = [cat for cat, score in dominant_categories]
    
    comments = []
    
    if top_track.domain == 'stem':
        comments.append("Votre profil montre un fort intérêt pour les sciences et technologies.")
    elif top_track.domain == 'business':
        comments.append("Vous semblez attiré(e) par le monde des affaires et du management.")
    elif top_track.domain == 'health':
        comments.append("Votre sens du service et intérêt pour les sciences de la vie ressortent clairement.")
    elif top_track.domain == 'arts':
        comments.append("Votre créativité et sens artistique sont vos atouts principaux.")
    elif top_track.domain == 'social':
        comments.append("Votre intérêt pour les relations humaines et la société est marqué.")
    
    if 'interest' in dominant_category_names:
        comments.append("Vos centres d'intérêt personnels guident fortement votre orientation.")
    if 'skill' in dominant_category_names:
        comments.append("Vos compétences actuelles correspondent bien à cette voie.")
    if 'personality' in dominant_category_names:
        comments.append("Votre personnalité semble particulièrement adaptée à ce domaine.")
    if 'value' in dominant_category_names:
        comments.append("Vos valeurs et priorités de vie orientent ce choix.")
    
    if top_track.difficulty >= 4:
        comments.append("Cette filière est exigeante mais votre profil montre les qualités nécessaires pour réussir.")
    elif top_track.difficulty <= 2:
        comments.append("Cette voie est accessible et offre de bonnes perspectives d'insertion.")
    
    return " ".join(comments)

def extract_user_profile_from_answers(answers):
    """
    Extrait un profil utilisateur basé sur les réponses au quiz.
    """
    from collections import Counter
    
    profile = {
        'preferred_domain': None,
        'preferred_difficulty': 'medium',
        'learning_style': 'balanced',
        'work_environment': 'varied',
    }
    
    domain_scores = {}
    difficulty_preferences = []
    work_environment_clues = []
    
    for answer in answers:
        choice = answer.choice
        if not choice:
            continue
            
        choice_text = choice.text.lower()
        
        # Domaines
        if any(word in choice_text for word in ['technique', 'scientifique', 'informatique', 'math']):
            domain_scores['stem'] = domain_scores.get('stem', 0) + 1
        if any(word in choice_text for word in ['commerce', 'gestion', 'management', 'entreprise']):
            domain_scores['business'] = domain_scores.get('business', 0) + 1
        if any(word in choice_text for word in ['santé', 'médecine', 'soin', 'biologie']):
            domain_scores['health'] = domain_scores.get('health', 0) + 1
        if any(word in choice_text for word in ['créatif', 'art', 'design', 'musique']):
            domain_scores['arts'] = domain_scores.get('arts', 0) + 1
        if any(word in choice_text for word in ['social', 'éducation', 'psychologie', 'aide']):
            domain_scores['social'] = domain_scores.get('social', 0) + 1
        
        # Difficulté
        if any(word in choice_text for word in ['facile', 'simple', 'accessible']):
            difficulty_preferences.append('easy')
        elif any(word in choice_text for word in ['challenge', 'difficile', 'complexe']):
            difficulty_preferences.append('challenging')
        else:
            difficulty_preferences.append('medium')
        
        # Environnement de travail
        if any(word in choice_text for word in ['bureau', 'ordinateur', 'intérieur']):
            work_environment_clues.append('office')
        elif any(word in choice_text for word in ['extérieur', 'terrain', 'voyage']):
            work_environment_clues.append('outdoor')
        elif any(word in choice_text for word in ['équipe', 'collaboration', 'groupe']):
            work_environment_clues.append('team')
        elif any(word in choice_text for word in ['autonome', 'seul', 'indépendant']):
            work_environment_clues.append('independent')
    
    # Déterminer le domaine préféré
    if domain_scores:
        profile['preferred_domain'] = max(domain_scores.items(), key=lambda x: x[1])[0]
    
    # Déterminer la difficulté préférée
    if difficulty_preferences:
        most_common = Counter(difficulty_preferences).most_common(1)
        if most_common:
            profile['preferred_difficulty'] = most_common[0][0]
    
    # Déterminer l'environnement de travail
    if work_environment_clues:
        env_count = Counter(work_environment_clues)
        if env_count:
            profile['work_environment'] = env_count.most_common(1)[0][0]
    
    return profile

def generate_learning_path(track, duration_weeks=12, weekly_hours=5):
    """
    Génère un chemin d'apprentissage personnalisé pour une filière.
    """
    from .models import YouTubePlaylist
    
    total_hours = duration_weeks * weekly_hours
    
    beginner_playlists = YouTubePlaylist.objects.filter(
        tracks=track,
        difficulty='beginner',
        is_active=True
    ).order_by('estimated_hours')[:3]
    
    intermediate_playlists = YouTubePlaylist.objects.filter(
        tracks=track,
        difficulty='intermediate', 
        is_active=True
    ).order_by('estimated_hours')[:3]
    
    advanced_playlists = YouTubePlaylist.objects.filter(
        tracks=track,
        difficulty='advanced',
        is_active=True
    ).order_by('estimated_hours')[:2]
    
    learning_path = {
        'track': track.name,
        'total_duration_weeks': duration_weeks,
        'weekly_hours': weekly_hours,
        'total_hours': total_hours,
        'phases': [
            {
                'phase': 1,
                'title': 'Fondamentaux',
                'weeks': f"1-{int(duration_weeks * 0.4)}",
                'description': f'Apprentissage des bases de {track.name}',
                'playlists': [
                    {
                        'id': p.id,
                        'title': p.title,
                        'estimated_hours': p.estimated_hours,
                        'difficulty': p.get_difficulty_display(),
                    }
                    for p in beginner_playlists
                ]
            },
            {
                'phase': 2,
                'title': 'Approfondissement',
                'weeks': f"{int(duration_weeks * 0.4) + 1}-{int(duration_weeks * 0.8)}",
                'description': 'Concepts intermédiaires et projets pratiques',
                'playlists': [
                    {
                        'id': p.id,
                        'title': p.title,
                        'estimated_hours': p.estimated_hours,
                        'difficulty': p.get_difficulty_display(),
                    }
                    for p in intermediate_playlists
                ]
            },
            {
                'phase': 3,
                'title': 'Spécialisation',
                'weeks': f"{int(duration_weeks * 0.8) + 1}-{duration_weeks}",
                'description': 'Concepts avancés et perfectionnement',
                'playlists': [
                    {
                        'id': p.id,
                        'title': p.title,
                        'estimated_hours': p.estimated_hours,
                        'difficulty': p.get_difficulty_display(),
                    }
                    for p in advanced_playlists
                ]
            }
        ]
    }
    
    return learning_path

def calculate_progress_metrics(user):
    """
    Calcule les métriques de progression d'un utilisateur.
    """
    from .models import UserPlaylistProgress
    
    user_progress = UserPlaylistProgress.objects.filter(user=user)
    
    total_playlists = user_progress.count()
    completed_playlists = user_progress.filter(is_completed=True).count()
    total_time_minutes = sum(progress.time_spent_minutes for progress in user_progress)
    total_time_hours = total_time_minutes // 60
    
    completion_rate = (completed_playlists / total_playlists * 100) if total_playlists > 0 else 0
    
    skill_level = "Débutant"
    if total_time_hours > 100:
        skill_level = "Expert"
    elif total_time_hours > 50:
        skill_level = "Intermédiaire"
    elif total_time_hours > 20:
        skill_level = "Avancé"
    
    recent_progress = user_progress.filter(
        updated_at__gte=timezone.now() - timedelta(days=30)
    )
    recent_completed = recent_progress.filter(is_completed=True).count()
    
    return {
        'total_playlists': total_playlists,
        'completed_playlists': completed_playlists,
        'completion_rate': round(completion_rate, 1),
        'total_time_hours': total_time_hours,
        'skill_level': skill_level,
        'recent_activity': recent_completed,
        'active_playlists': user_progress.filter(is_completed=False).count()
    }