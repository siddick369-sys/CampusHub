import os
import json
import uuid
from groq import Groq
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from accounts.decorators import student_required

from .models import (
    Track,
    School,
    Job,
    Question,
    Choice,
    ChoiceTrackScore,
    OrientationResult,
    OrientationAnswer,
    AIOrientationSession,
)
from .forms import OrientationTestForm

# Configuration Groq pour l'orientation
GROQ_API_KEY_ORIENTATION = os.getenv("GROQ_API_KEY")
groq_orientation_client = None
if GROQ_API_KEY_ORIENTATION:
    groq_orientation_client = Groq(api_key=GROQ_API_KEY_ORIENTATION)


# -------------------------------------------------------
# DASHBOARD ÉTUDIANT ORIENTATION
# -------------------------------------------------------

@student_required
def orientation_dashboard(request):
    """
    Dashboard simple :
      - dernier résultat
      - lien vers test
      - lien vers filières / historique
    """
    last_result = (
        OrientationResult.objects
        .filter(user=request.user)
        .order_by('-created_at')
        .first()
    )

    context = {
        'last_result': last_result,
    }
    return render(request, 'orientation/dashboard.html', context)


@student_required
def orientation_history_view(request):
    """
    Historique des tests passés par l'étudiant.
    """
    results = OrientationResult.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orientation/history.html', {'results': results})


# -------------------------------------------------------
# FILIÈRES : LISTE, DÉTAIL, RECHERCHE
# -------------------------------------------------------

@login_required
def track_list_view(request):
    tracks = Track.objects.filter(is_active=True).order_by('name')
    return render(request, 'orientation/track_list.html', {'tracks': tracks})


@login_required
def track_detail_view(request, slug):
    track = get_object_or_404(Track, slug=slug, is_active=True)
    schools = track.schools.all().order_by('-ranking_score', 'name')
    jobs = track.jobs.all().order_by('-jobtrackrelevance__relevance_score', 'title')

    context = {
        'track': track,
        'schools': schools,
        'jobs': jobs,
    }
    return render(request, 'orientation/track_detail.html', context)


@login_required
def track_search_view(request):
    """
    Recherche / filtrage des filières par :
      - mot-clé
      - domaine
      - difficulté
    """
    q = request.GET.get('q')
    domain = request.GET.get('domain')
    difficulty = request.GET.get('difficulty')

    tracks = Track.objects.filter(is_active=True)

    if q:
        tracks = tracks.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(main_skills__icontains=q)
        )

    if domain:
        tracks = tracks.filter(domain=domain)

    if difficulty:
        try:
            d = int(difficulty)
            tracks = tracks.filter(difficulty=d)
        except ValueError:
            pass

    tracks = tracks.order_by('name')

    context = {
        'tracks': tracks,
    }
    return render(request, 'orientation/track_search.html', context)


# -------------------------------------------------------
# ÉCOLES & MÉTIERS
# -------------------------------------------------------

@login_required
def school_detail_view(request, pk):
    school = get_object_or_404(School, pk=pk)
    tracks = school.tracks.all()
    return render(request, 'orientation/school_detail.html', {
        'school': school,
        'tracks': tracks,
    })


@login_required
def job_detail_view(request, pk):
    job = get_object_or_404(Job, pk=pk)
    tracks = job.tracks.all().order_by('-jobtrackrelevance__relevance_score', 'name')
    return render(request, 'orientation/job_detail.html', {
        'job': job,
        'tracks': tracks,
    })


# -------------------------------------------------------
# TEST D'ORIENTATION
# -------------------------------------------------------

@student_required
def orientation_test_view(request):
    """Redirige vers le nouveau test d'orientation IA dynamique."""
    return redirect('ai_orientation_test')

    if request.method == 'POST':
        form = OrientationTestForm(request.POST, questions=questions)
        if form.is_valid():
            # 1) Récupérer les choix sélectionnés pour chaque question
            question_choices = {}
            for question in questions:
                field_name = f"question_{question.id}"
                choice = form.cleaned_data.get(field_name)
                question_choices[question] = choice

            # 2) Calculer les scores par filière et par catégorie
            track_scores = {}      # {track_id: score_total}
            category_scores = {}   # {category: score_total}

            for question, choice in question_choices.items():
                if not choice:
                    continue

                cts_qs = ChoiceTrackScore.objects.filter(choice=choice)
                total_for_question = 0

                for cts in cts_qs:
                    track_id = cts.track_id
                    score = cts.score

                    track_scores[track_id] = track_scores.get(track_id, 0) + score
                    total_for_question += score

                if total_for_question > 0:
                    cat = question.category
                    category_scores[cat] = category_scores.get(cat, 0) + total_for_question

            if not track_scores:
                messages.error(
                    request,
                    "Impossible de calculer un résultat : reliez d'abord les choix aux filières dans l'admin."
                )
                return redirect('orientation_test')

            # 3) Déterminer les filières recommandées (top 3)
            sorted_tracks = sorted(
                track_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_track_ids = [t[0] for t in sorted_tracks[:3]]

            # 4) Créer le résultat
            result = OrientationResult.objects.create(
                user=request.user,
                scores_data={
                    "tracks": track_scores,
                    "categories": category_scores,
                },
            )

            result.suggested_tracks.set(Track.objects.filter(id__in=top_track_ids))

            # 5) Enregistrer les réponses détaillées
            answers = []
            for question, choice in question_choices.items():
                answers.append(
                    OrientationAnswer(
                        result=result,
                        question=question,
                        choice=choice,
                    )
                )
            OrientationAnswer.objects.bulk_create(answers)

            messages.success(request, "Test terminé. Voici vos résultats d'orientation.")
            return redirect('orientation_result_detail', result_id=result.id)
    else:
        form = OrientationTestForm(questions=questions)

    return render(request, 'orientation/orientation_test.html', {'form': form})


@student_required
def orientation_result_detail_view(request, result_id):
    """
    Affiche le détail d'un résultat :
      - filières recommandées
      - scores
      - raisonnement IA
      - recommandations YouTube
    """
    result = get_object_or_404(OrientationResult, id=result_id, user=request.user)

    track_scores = (result.scores_data or {}).get("tracks", {}) or {}
    category_scores = (result.scores_data or {}).get("categories", {}) or {}
    ai_reasoning = (result.scores_data or {}).get("ai_reasoning", "")

    # Récupérer les tracks avec les écoles pré-chargées
    suggested_tracks = result.suggested_tracks.all().prefetch_related('schools')
    
    track_score_list = []
    for track in suggested_tracks:
        score = track_scores.get(str(track.id)) or track_scores.get(track.id) or 0
        track_score_list.append((track, score))
    
    track_score_list.sort(key=lambda x: x[1], reverse=True)
    
    # Recommandations YouTube
    from .services import recommend_youtube_playlists
    youtube_playlists = recommend_youtube_playlists(result)

    context = {
        'result': result,
        'track_score_list': track_score_list,
        'category_scores': category_scores,
        'ai_reasoning': ai_reasoning,
        'youtube_playlists': youtube_playlists,
    }
    return render(request, 'orientation/orientation_result.html', context)


@login_required
def orientation_test_page(request):
    return render(request,"orientation/test_orientation.html")


from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import School, Track



@login_required
def school_search_view(request):
    """
    Moteur de recherche avancé des écoles :
    - mot-clé (nom, ville, adresse, frais)
    - ville
    - pays
    - type d’école (publique / privée / en ligne)
    - filière (Track)
    - budget approximatif (bas / moyen / élevé via tuition_range)
    - écoles partenaires uniquement
    """
    q = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    country = request.GET.get('country', '').strip()
    school_type = request.GET.get('school_type', '').strip()
    track_id = request.GET.get('track', '').strip()
    budget = request.GET.get('budget', '').strip()  # low / medium / high
    partner_only = request.GET.get('partner', '') == '1'

    schools = School.objects.all().prefetch_related('tracks')

    # Mot-clé global
    if q:
        schools = schools.filter(
            Q(name__icontains=q) |
            Q(short_name__icontains=q) |
            Q(city__icontains=q) |
            Q(country__icontains=q) |
            Q(address__icontains=q) |
            Q(tuition_range__icontains=q)
        )

    # Ville
    if city:
        schools = schools.filter(city__icontains=city)

    # Pays
    if country:
        schools = schools.filter(country__icontains=country)

    # Type d’école (public / private / online)
    if school_type:
        schools = schools.filter(school_type=school_type)

    # Filtre par filière (Track)
    if track_id:
        try:
            tid = int(track_id)
            schools = schools.filter(tracks__id=tid)
        except ValueError:
            pass

    # Budget approximatif basé sur la chaîne tuition_range
    # (très simplifié mais suffisant pour un MVP)
    if budget == 'low':
        # Ex: 50k - 150k FCFA, frais faibles
        schools = schools.filter(
            Q(tuition_range__icontains="50k") |
            Q(tuition_range__icontains="100k") |
            Q(tuition_range__icontains="150k") |
            Q(tuition_range__icontains="200k")
        )
    elif budget == 'medium':
        # Ex: 300k - 800k FCFA
        schools = schools.filter(
            Q(tuition_range__icontains="300k") |
            Q(tuition_range__icontains="400k") |
            Q(tuition_range__icontains="450k") |
            Q(tuition_range__icontains="500k") |
            Q(tuition_range__icontains="600k") |
            Q(tuition_range__icontains="700k") |
            Q(tuition_range__icontains="800k")
        )
    elif budget == 'high':
        # Ex: 900k+, 1.2M, 2M...
        schools = schools.filter(
            Q(tuition_range__icontains="900k") |
            Q(tuition_range__icontains="1.2M") |
            Q(tuition_range__icontains="1.5M") |
            Q(tuition_range__icontains="2M") |
            Q(tuition_range__icontains="Élevée") |
            Q(tuition_range__icontains="elevée") |
            Q(tuition_range__icontains="international")
        )

    # Écoles partenaires uniquement
    if partner_only:
        schools = schools.filter(is_partner=True)

    schools = schools.order_by('-ranking_score', 'name').distinct()

    # Pour le select des filières
    tracks = Track.objects.filter(is_active=True).order_by('name')

    context = {
        "schools": schools,
        "tracks": tracks,
        # Pour garder les valeurs dans le formulaire
        "params": {
            "q": q,
            "city": city,
            "country": country,
            "school_type": school_type,
            "track": track_id,
            "budget": budget,
            "partner": '1' if partner_only else '',
        },
    }
    return render(request, "orientation/school_search.html", context)


# orientation/services.py

    
# orientation/views.py
from django.shortcuts import render, get_object_or_404
from .models import OrientationResult
from .services import recommend_youtube_playlists

def orientation_result_with_content(request, result_id):
    """
    Affiche le résultat d'orientation avec les recommandations YouTube.
    """
    result = get_object_or_404(
        OrientationResult, 
        id=result_id, 
        user=request.user
    )
    
    # Récupérer les recommandations
    youtube_playlists = recommend_youtube_playlists(result)
    
    # Préparer les données pour le template
    tracks_with_scores = result.get_sorted_tracks()
    top_track = tracks_with_scores[0][0] if tracks_with_scores else None
    
    context = {
        'result': result,
        'tracks_with_scores': tracks_with_scores,
        'youtube_playlists': youtube_playlists,
        'top_track': top_track,
    }
    
    return render(request, 'orientation/result_with_content.html', context)

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Job

def job_list_view(request):
    """
    Affiche la liste des métiers avec filtrage par recherche et secteur.
    """
    query = request.GET.get('q')
    sector_filter = request.GET.get('sector')

    # On récupère tous les métiers (triés par les plus récents)
    jobs = Job.objects.all().order_by('-created_at')

    # Filtrage par recherche textuelle (titre ou description)
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(sector__icontains=query)
        )

    # Filtrage par secteur d'activité
    if sector_filter:
        jobs = jobs.filter(sector=sector_filter)

    # Récupération de la liste des secteurs pour le dropdown du filtre
    # On prend les secteurs uniques qui ne sont pas vides
    sectors = Job.objects.values_list('sector', flat=True).distinct().exclude(sector__isnull=True).exclude(sector='')

    context = {
        'jobs': jobs,
        'sectors': sectors,
    }
    return render(request, 'orientation/job_list.html', context)


def job_detail_view(request, pk):
    """
    Affiche les détails d'un métier spécifique.
    Les relations avec les filières (Track) sont gérées via JobTrackRelevance.
    """
    job = get_object_or_404(Job, pk=pk)
    
    # Note : Dans le template, on accède aux filières liées via :
    # job.jobtrackrelevance_set.all
    
    context = {
        'job': job,
    }
    return render(request, 'orientation/job_detail.html', context)



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import OrientationResult, Job, JobTrackRelevance

@login_required
def orientation_job_recommendations(request):
    # 1. On récupère le dernier résultat du test de l'utilisateur
    result = OrientationResult.objects.filter(user=request.user).order_by('-created_at').first()

    if not result:
        return redirect('orientation_test') # Redirige vers le test si aucun résultat

    # 2. On récupère les filières suggérées (triées par score via ta méthode de modèle)
    sorted_tracks_with_scores = result.get_sorted_tracks()
    
    # On ne garde que les 3 meilleures filières pour ne pas surcharger
    top_tracks = [item[0] for item in sorted_tracks_with_scores[:3]]

    # 3. On récupère les métiers liés à ces filières spécifiques
    # On utilise select_related et prefetch_related pour la performance
    recommended_jobs = Job.objects.filter(
        jobtrackrelevance__track__in=top_tracks
    ).distinct().order_by('-demand_level', '-typical_salary_max')

    context = {
        'result': result,
        'top_tracks': top_tracks,
        'recommended_jobs': recommended_jobs,
    }
    return render(request, 'orientation/recommended_jobs.html', context)

@student_required
def ai_orientation_test_view(request):
    """
    Affiche la page du test d'orientation IA.
    """
    # Générer un ID de session unique si nécessaire
    session_id = str(uuid.uuid4())
    return render(request, 'orientation/ai_test.html', {'session_id': session_id})


@csrf_exempt
@student_required
def ai_orientation_api(request):
    """
    API pour gérer la conversation d'orientation avec Groq.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id")
        is_start = data.get("is_start", False)
        is_final_request = data.get("is_final_request", False)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)

    from accounts.services import UsageManager

    # 1. Vérification du quota au démarrage
    if is_start:
        if not UsageManager.is_action_allowed(request.user, 'test_ia'):
            return JsonResponse({
                "error": "quota_exceeded",
                "message": "Quota de tests IA atteint. Veuillez passer au Premium ou acheter un test individuel.",
                "redirect_url": f"{reverse('payments:initiate_payment')}?action=test_ia&amount=500"
            })

    if not session_id:
        return JsonResponse({"error": "Session ID requis"}, status=400)

    # Récupérer ou créer la session
    session, created = AIOrientationSession.objects.get_or_create(
        session_id=session_id,
        defaults={'user': request.user, 'history': []}
    )

    if session.is_finished:
        return JsonResponse({"error": "Test déjà terminé"}, status=400)

    # Contexte des filières pour l'IA
    tracks = Track.objects.filter(is_active=True)
    tracks_context = "\n".join([f"- {t.name} (Code: {t.code}): {t.description}" for t in tracks])

    system_instruction = f"""
    Tu es l'expert en orientation de CampusHub. Ta mission est d'aider l'étudiant à trouver sa voie via un test conversationnel.
    
    FILIÈRES DISPONIBLES :
    {tracks_context}
    
    DIRECTIVES :
    1. Commence par une salutation chaleureuse et explique que tu vas poser quelques questions (environ 5-7) pour le connaître.
    2. Pose UNE SEULE question à la fois. Les questions doivent porter sur ses intérêts, ses forces, ses valeurs et ses ambitions.
    3. Sois adaptatif : si l'étudiant donne une réponse courte, demande des précisions. Si la réponse est claire, passe à un autre aspect.
    4. Après environ 6 questions pertinentes, annonce que tu as assez d'éléments pour conclure.
    5. POUR CONCLURE : Tu DOIS renvoyer un bloc JSON précis à la fin de ton message final sous la forme :
       RESULTAT_FINAL: {{"reasoning": "Explications...", "recommandations": ["CODE1", "CODE2", "CODE3"]}}
       Remplace CODE1, CODE2 par les CODES des filières (ex: INF-LIC). Choisis exactement 3 filières par ordre de pertinence.
    
    TON TON : Encourageant, professionnel et empathique.
    LANGUE : Français uniquement.
    """

    messages = [{"role": "system", "content": system_instruction}]
    for h in session.history:
        messages.append({"role": h["role"], "content": h["content"]})

    if is_final_request:
        messages.append({"role": "system", "content": "IMPORTANT: L'utilisateur souhaite terminer le test maintenant. Analyse ses réponses précédentes et fournis IMMÉDIATEMENT ton bloc RESULTAT_FINAL with tes conclusions."})
    elif not is_start and user_message:
        messages.append({"role": "user", "content": user_message})
        session.history.append({"role": "user", "content": user_message})

    try:
        if not groq_orientation_client:
            return JsonResponse({"error": "L'expert en orientation est désactivé (Clé API manquante)."})

        completion = groq_orientation_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.6,
        )
        ai_response = completion.choices[0].message.content
        session.history.append({"role": "assistant", "content": ai_response})

        # Vérifier si c'est la fin (présence du tag RESULTAT_FINAL)
        if "RESULTAT_FINAL:" in ai_response:
            try:
                # Extraction robuste du JSON (au cas où l'IA ajoute du texte autour)
                import re
                json_match = re.search(r'\{.*\}', ai_response.split("RESULTAT_FINAL:")[1], re.DOTALL)
                if not json_match:
                    raise ValueError("Format JSON non trouvé après RESULTAT_FINAL:")
                
                result_data = json.loads(json_match.group(0))
                
                # Créer le résultat Django officiel
                codes = result_data.get("recommandations", [])
                suggested_tracks = Track.objects.filter(code__in=codes)
                
                # Mapper les scores (arbitraire pour l'IA)
                fake_scores = {str(t.id): (10 if i == 0 else 7 if i == 1 else 5) for i, t in enumerate(suggested_tracks)}
                
                final_result = OrientationResult.objects.create(
                    user=request.user,
                    scores_data={
                        "tracks": fake_scores, 
                        "categories": {}, 
                        "ai_reasoning": result_data.get("reasoning")
                    },
                    comment=ai_response.split("RESULTAT_FINAL:")[0].strip()
                )
                final_result.suggested_tracks.set(suggested_tracks)
                
                # --- NOUVEAU : Mettre à jour le profil utilisateur ---
                profile = getattr(request.user, "profile", None)
                if profile and suggested_tracks.exists():
                    # On prend la première recommandation comme filière souhaitée
                    profile.student_field = suggested_tracks.first().name
                    profile.save()

                # --- NOUVEAU : Créer des réponses pour l'historique ---
                try:
                    from .models import Question, OrientationAnswer
                    generic_question, _ = Question.objects.get_or_create(
                        text="Résumé de l'analyse IA",
                        defaults={'category': 'interest', 'order': 999}
                    )
                    OrientationAnswer.objects.create(
                        result=final_result,
                        question=generic_question,
                        choice=None
                    )
                    # Incrémenter le quota
                    UsageManager.increment_usage(request.user, 'test_ia')
                except Exception as ex:
                    print(f"Erreur création OrientationAnswer IA: {ex}")

                session.is_finished = True
                session.final_recommendation = ai_response
                session.save()
                
                return JsonResponse({
                    "response": ai_response.split("RESULTAT_FINAL:")[0].strip(),
                    "is_finished": True,
                    "redirect_url": reverse('orientation_result_detail', args=[final_result.id])
                })
            except Exception as e:
                print(f"Erreur parsing résultat final : {e}")

        session.save()
        return JsonResponse({"response": ai_response, "is_finished": False})

    except Exception as e:
        print(f"Erreur API Groq : {e}")
        return JsonResponse({"error": "Erreur serveur Groq"}, status=500)