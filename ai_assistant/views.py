import json
import logging
import os
from groq import Groq
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import AICachedResponse, AIChatSession
from .utils import normalize_question

logger = logging.getLogger(__name__)

# Configuration du modèle Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

def call_llm_api(prompt):
    """
    Appelle l'API Groq avec un contexte complet sur CampusHub.
    """
    if not GROQ_API_KEY:
        return "L'assistant est en mode démo (Clé API Groq manquante). Voici une simulation : " + prompt[:50] + "..."

    # Connaissances approfondies de CampusHub
    project_context = """
    CAMPUSHUB - LA PLATEFORME UNIVERSITAIRE INTÉGRÉE
    Vision : Pont entre Étudiants, Entreprises et Prestataires.
    
    1. ORIENTATION (`orientation`) : 
       - Test d'IA pour suggérer des carrières.
       - Catalogue de filières (STEM, Business, Santé, Arts).
       - Playlists YouTube tutoriels intégrées.
       - Base de données des écoles.
    
    2. INSERTION PRO (`stages`) :
       - Bourse de stages/emplois.
       - Suivi des candidatures en temps réel.
       - Centralisation CV/Portfolios.
       - Système de feedback sur les stages.
       
    3. MARKETPLACE (`services`) :
       - Services de proximité (Freelance étudiant, cours, design).
       - Packs Basic/Standard/Premium.
       - Trust Score (Score de confiance algorithmique).
       
    4. INNOVATION (`incubation`) :
       - Vitrine de projets étudiants.
       - Challenges Entreprise (Concours/Hackathons).
       - Coach d'entretien IA (Simulation réaliste).
       
    5. TECH STACK : Django 3.11, Django Channels (Temps réel), Celery/Redis (Async/Cache), Groq/Llama 3 (IA).
    
    6. ÉQUIPE : 
       - Aboubakar Ibrahim Siddick (Fullstack Architecture).
       - Acko'o Suzanne (Frontend).
       - Tala Maryam Ousmanou (UI/UX Design).
    """

    system_instruction = (
        "Tu es l'assistant intelligent OFFICIEL de CampusHub. "
        "Ta mission est de renseigner les utilisateurs sur TOUT ce qui touche à la plateforme. "
        "Utilise les connaissances suivantes pour répondre avec précision :\n"
        f"{project_context}\n"
        "RÈGLES :\n"
        "- Sois chaleureux, professionnel et concis.\n"
        "- Parle toujours en français.\n"
        "- Si on te demande qui t'a créé : Cite l'équipe (Aboubakar, Suzanne, Maryam).\n"
        "- Si on pose une question hors-sujet : Rappelle poliment que tu es là pour CampusHub."
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    
    return chat_completion.choices[0].message.content

@csrf_exempt
def ai_chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        user_question = data.get("question", "").strip()
        session_id = data.get("session_id", "default_session")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Données JSON invalides"}, status=400)

    if not user_question:
        return JsonResponse({"error": "La question est vide"}, status=400)

    # 1. Normalisation
    normalized_q = normalize_question(user_question)

    # 2. Recherche dans le cache
    cached = AICachedResponse.objects.filter(question_normalisee=normalized_q).first()
    
    if cached:
        # Update cache stats
        cached.compteur_utilisation += 1
        cached.save()
        response_text = cached.reponse
        source = "cache"
    else:
        # 3. Appel API LLM
        try:
            response_text = call_llm_api(user_question)
            
            # 4. Sauvegarde dans le cache
            AICachedResponse.objects.create(
                question_originale=user_question,
                question_normalisee=normalized_q,
                reponse=response_text
            )
            source = "api"
        except Exception as e:
            logger.error(f"Erreur API LLM: {str(e)}")
            return JsonResponse({"error": "L'assistant IA est indisponible pour le moment."}, status=503)

    # 5. Gestion de l'historique de session
    session, created = AIChatSession.objects.get_or_create(
        session_id=session_id,
        defaults={"user": request.user if request.user.is_authenticated else None}
    )
    
    history = session.history
    history.append({"role": "user", "content": user_question, "timestamp": timezone.now().isoformat()})
    history.append({"role": "assistant", "content": response_text, "timestamp": timezone.now().isoformat()})
    
    # Garder seulement les 20 derniers messages pour éviter une explosion du JSON
    session.history = history[-20:]
    session.save()

    return JsonResponse({
        "response": response_text,
        "source": source,
        "history_count": len(session.history)
    })
