# orientation/services.py

from .models import YouTubePlaylist


def recommend_youtube_playlists(orientation_result, max_recommendations=6):
    """
    Recommande des playlists YouTube basées sur les résultats d'orientation.
    """
    from .models import YouTubePlaylist, Track
    
    # Récupérer les filières suggérées (triées par score)
    tracks_with_scores = orientation_result.get_sorted_tracks()
    
    if not tracks_with_scores:
        return YouTubePlaylist.objects.none()
    
    # Extraire les IDs des filières (priorité aux meilleurs scores)
    track_ids = [track.id for track, score in tracks_with_scores[:3]]  # Top 3 filières
    
    # Critères de recommandation
    recommendations = YouTubePlaylist.objects.filter(
        tracks__id__in=track_ids,
        is_active=True
    ).distinct()
    
    # Prioriser par difficulté (débutant d'abord)
    difficulty_order = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
    recommendations = sorted(
        recommendations,
        key=lambda x: difficulty_order.get(x.difficulty, 1)
    )
    
    return recommendations[:max_recommendations]

def get_track_specific_playlists(track, limit=4):
    """
    Récupère les playlists spécifiques à une filière.
    """
    return YouTubePlaylist.objects.filter(
        tracks=track,
        is_active=True
    ).order_by('difficulty')[:limit]