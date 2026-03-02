from django.shortcuts import render

def privacy_policy_view(request):
    """
    Affiche la politique de confidentialité et RGPD.
    """
    return render(request, "legal/privacy_policy.html")

def terms_conditions_view(request):
    """
    Affiche les Conditions Générales d'Utilisation (CGU/CGV).
    """
    return render(request, "legal/terms_conditions.html")
    
def legal_notices_view(request):
    """
    Affiche les Mentions Légales (Obligatoire).
    """
    return render(request, "legal/legal_notices.html")

def how_it_works_view(request):
    """Page explicative + FAQ"""
    return render(request, "legal/how_it_works.html")



import os
from groq import Groq
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# --- CONFIGURATION CLIENT GROQ ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# --- LA CARTE DU SITE INTELLIGENTE ---
# ... (SITE_MAP reste inchangé) ...

# --- LA CARTE DU SITE INTELLIGENTE ---
# Clé = 'name' dans urls.py | Valeur = Description naturelle pour l'IA
SITE_MAP = {
    # --- GÉNÉRAL & COMPTE ---
    'home': 'Accueil, page de bienvenue, retour au début',
    'about': 'À propos, qui sommes nous, l\'équipe, présentation',
    'profile_edit': 'Modifier mon profil, changer mes infos, paramètres compte',
    'register': 'Inscription, créer un compte, rejoindre',
    'login': 'Connexion, se connecter, login',
    'logout': 'Déconnexion, se déconnecter, quitter',
    'how_it_works': 'Aide, comment ça marche, tutoriel',
    'messaging_inbox': 'Messagerie, mes messages, discussions, chat, inbox',
    'notifications_list': 'Notifications, mes alertes, nouveautés',
    'trust_score_dashboard': 'Mon trust score, score de confiance, réputation',

    # --- STAGES & EMPLOI (ÉTUDIANT) ---
    'student_dashboard': 'Tableau de bord étudiant, mon espace stage, statistiques étudiant',
    'offer_list': 'Liste des offres de stage, chercher un job, voir les stages, offres d\'emploi',
    'student_applications': 'Mes candidatures, suivi des demandes, mes postulations',
    'recommended_offers': 'Offres recommandées, stages pour moi, suggestions',
    'student_cv_generate': 'Générer mon CV, créer un CV, télécharger CV',
    'motivation_letter_template': 'Modèle lettre de motivation, rédiger lettre',

    # --- STAGES & EMPLOI (ENTREPRISE) ---
    'company_dashboard': 'Tableau de bord entreprise, gestion recruteur, espace pro',
    'company_offers': 'Mes offres publiées, gérer mes annonces, mes stages',
    'company_offer_create': 'Publier une offre, créer un stage, poster un job, recruter',
    'company_verification_request': 'Vérifier mon entreprise, badge vérifié',
    'company_subscription_plans': 'Plans d\'abonnement entreprise, tarifs pro',

    # --- SERVICES & FREELANCE ---
    'service_list': 'Trouver un freelance, services disponibles, prestations, marketplace',
    'service_create': 'Créer un service, devenir vendeur, proposer une prestation, publier service',
    'provider_dashboard': 'Tableau de bord prestataire, espace vendeur, mes ventes',
    'provider_orders_list': 'Mes commandes reçues, gérer les commandes',
    'my_favorite_services': 'Services favoris, freelances sauvegardés',
    'become_provider': 'Devenir prestataire, commencer à vendre',

    # --- INCUBATION & PROJETS ---
    'liste_projets': 'Liste des projets, startups, découvrir les projets',
    'creer_projet': 'Créer un projet, lancer ma startup, soumettre une idée',
    'liste_challenges': 'Liste des challenges, concours, hackathons',
    'creer_challenge': 'Lancer un challenge, créer une compétition',
    'mes_alertes': 'Mes alertes incubation, notifications projets',

    # --- ORIENTATION & ÉCOLES ---
    'orientation_dashboard': 'Tableau de bord orientation, mon parcours',
    'school_search': 'Chercher une école, trouver une université, liste des établissements',
    'track_list': 'Liste des filières, spécialités, formations',
    'orientation_test_page': 'Passer un test d\'orientation, quiz métier',
    'orientation_history': 'Historique de mes tests, mes résultats',

    # --- COACH IA ---
    'start_coach': 'Coach IA, simulation entretien, m\'entraîner, interview virtuelle',
}

@csrf_exempt 
def voice_navigation_api(request):
    if request.method == 'POST':
        user_command = request.POST.get('command', '')
        
        if not user_command:
            return JsonResponse({'status': 'error', 'message': 'Commande vide'})

        # Prompt optimisé pour Gemini
        prompt = f"""
        Tu es le système de navigation intelligent du site "CampusHub".
        
        LISTE DES PAGES DISPONIBLES (Nom technique : Description) :
        {SITE_MAP}

        DEMANDE DE L'UTILISATEUR : "{user_command}"

        TA MISSION :
        1. Analyse l'intention de l'utilisateur.
        2. Trouve la page la plus pertinente dans la liste.
        3. Si l'utilisateur demande quelque chose de vague (ex: "Je veux travailler"), dirige-le vers la liste des offres ('offer_list').
        4. Si l'utilisateur veut vendre, dirige-le vers 'service_create' ou 'become_provider'.
        
        RÉPONSE ATTENDUE :
        Réponds UNIQUEMENT avec le 'Nom technique' (la clé du dictionnaire). 
        Si aucune page ne correspond, réponds 'None'.
        Ne mets pas de phrases, pas de ponctuation, juste le mot clé.
        """

        try:
            if not groq_client:
                 return JsonResponse({'status': 'error', 'message': "L'assistant vocal est désactivé (Clé API manquante)."})

            # Appel rapide à Llama 3 via Groq
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.1-8b-instant",
            )
            url_name = chat_completion.choices[0].message.content.strip().replace("'", "").replace('"', "").replace("`", "")
            
            if url_name in SITE_MAP:
                # On génère l'URL réelle grâce à Django reverse()
                target_url = reverse(url_name)
                page_desc = SITE_MAP[url_name].split(',')[0] # On prend juste le 1er mot de description
                
                return JsonResponse({
                    'status': 'success', 
                    'redirect_url': target_url, 
                    'page_name': page_desc
                })
            else:
                return JsonResponse({'status': 'error', 'message': "Je ne trouve pas cette page."})

        except Exception as e:
            # Fallback en cas d'erreur URL (ex: reverse échoue) ou erreur IA
            print(f"Erreur Nav: {e}")
            return JsonResponse({'status': 'error', 'message': "Erreur technique de navigation."})

    return JsonResponse({'status': 'error'}, status=400)