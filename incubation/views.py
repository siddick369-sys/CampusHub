from django.shortcuts import render

# Create your views here.


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ProjetInnovation, ChallengeEntreprise, ParticipationChallenge
from .forms import ProjetForm, ParticipationForm
from stages.models import Conversation, Message

# --- VUES PROJETS ÉTUDIANTS ---

@login_required
def creer_projet(request):
    profile = request.user.profile
    
    # Vérification : Seuls les étudiants peuvent créer un projet
    if profile.role != 'student':
        messages.error(request, "Seuls les étudiants peuvent lancer une startup sur CampusHub.")
        return redirect('home') # Ou ton dashboard

    from accounts.services import UsageManager
    from django.urls import reverse

    # 1. Vérification du quota
    if not UsageManager.is_action_allowed(request.user, 'project_publication'):
        messages.warning(request, "Quota de publication de projets atteint.")
        return redirect(f"{reverse('payments:initiate_payment')}?action=project_publication&amount=1000")

    if request.method == 'POST':
        form = ProjetForm(request.POST, request.FILES)
        if form.is_valid():
            projet = form.save(commit=False)
            projet.porteur = profile # On assigne l'étudiant connecté
            projet.save()
            form.save_m2m() # Important pour sauvegarder les compétences (Many-to-Many)
            
            # 2. Incrémenter le quota
            UsageManager.increment_usage(request.user, 'project_publication')
            
            messages.success(request, "Votre projet a été lancé avec succès ! 🚀")
            return redirect('liste_projets') # À créer
    else:
        form = ProjetForm()

    return render(request, 'incubateur/creer_projet.html', {'form': form})

from .models import ProjetInnovation, ProjetSearchAlert, ChallengeSearchAlert # Importe le nouveau modèle
# --- MISE À JOUR DE LA VUE MES ALERTES (Pour gérer les 2 types) ---
from django.core.paginator import Paginator
from django.db.models import Count, Q

@login_required
def liste_challenges(request):
    query = request.GET.get('q', '').strip()
    tri = request.GET.get('tri', 'recent') # recent, fin_proche, populaire
    
    # 1. OPTIMISATION SQL : On charge l'entreprise et on compte les participants
    challenges = ChallengeEntreprise.objects.filter(is_active=True)\
        .select_related('entreprise__user')\
        .annotate(nb_participants=Count('participationchallenge'))

    # 2. RECHERCHE TEXTUELLE
    if query:
        challenges = challenges.filter(
            Q(titre__icontains=query) | 
            Q(description__icontains=query) |
            Q(recompense__icontains=query)
        )
        # Logique d'alerte (avec quota)
        if not challenges.exists():
            from accounts.services import UsageManager
            if UsageManager.is_action_allowed(request.user, 'search_alerts_count'):
                obj, created = ChallengeSearchAlert.objects.get_or_create(
                    user=request.user.profile, query=query.lower()
                )
                if created:
                    messages.info(request, f"Alerte créée pour '{query}'.")
            else:
                messages.warning(request, "Impossible de créer l'alerte : quota atteint.")

    # 3. TRI (SORTING)
    if tri == 'fin_proche':
        challenges = challenges.order_by('date_limite')
    elif tri == 'populaire':
        challenges = challenges.order_by('-nb_participants')
    else: # Par défaut : plus récent
        challenges = challenges.order_by('-created_at')

    # 4. PAGINATION (9 challenges par page)
    paginator = Paginator(challenges, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'incubateur/liste_challenges.html', {
        'challenges': page_obj, # On passe l'objet paginé
        'query': query,
        'tri': tri
    })

@login_required
def liste_projets(request):
    query = request.GET.get('q', '').strip()
    filtre_stade = request.GET.get('stade', '') # IDEE, MVP, DEV, LIVE
    
    # 1. OPTIMISATION : On charge le porteur et les compétences (tags)
    projets = ProjetInnovation.objects.all()\
        .select_related('porteur__user')\
        .prefetch_related('competences_recherchees', 'likes','porteur__badges_obtenus__badge')\
        .annotate(nb_likes=Count('likes'))

    # 2. FILTRES
    if filtre_stade:
        projets = projets.filter(stade=filtre_stade)

    if query:
        projets = projets.filter(
            Q(titre__icontains=query) | 
            Q(description_courte__icontains=query) |
            Q(competences_recherchees__nom__icontains=query)
        ).distinct()
        # Logique d'alerte (avec quota)
        if not projets.exists():
            from accounts.services import UsageManager
            if UsageManager.is_action_allowed(request.user, 'search_alerts_count'):
                from .models import ProjetSearchAlert
                obj, created = ProjetSearchAlert.objects.get_or_create(
                    user=request.user.profile, query=query.lower()
                )
                if created:
                    messages.info(request, f"Alerte créée pour '{query}'.")
            else:
                messages.warning(request, "Impossible de créer l'alerte : quota atteint.")

    # 3. TRI PAR DÉFAUT (Les plus likés en premier, puis les récents)
    projets = projets.order_by('-nb_likes', '-created_at')

    # 4. PAGINATION
    paginator = Paginator(projets, 12) # 12 projets par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'incubateur/liste_projets.html', {
        'projets': page_obj,
        'query': query,
        'filtre_stade': filtre_stade
    })
@login_required
def mes_alertes(request):
    profile = request.user.profile
    
    # On récupère les deux types d'alertes
    alertes_challenges = ChallengeSearchAlert.objects.filter(user=profile).order_by('-created_at')
    alertes_projets = ProjetSearchAlert.objects.filter(user=profile).order_by('-created_at')

    if request.method == "POST":
        alerte_id = request.POST.get('alerte_id')
        type_alerte = request.POST.get('type_alerte') # 'challenge' ou 'projet'
        
        if type_alerte == 'challenge':
            ChallengeSearchAlert.objects.filter(id=alerte_id, user=profile).delete()
            messages.success(request, "Alerte Challenge supprimée.")
            
        elif type_alerte == 'projet':
            ProjetSearchAlert.objects.filter(id=alerte_id, user=profile).delete()
            messages.success(request, "Alerte Projet supprimée.")
            
        return redirect('mes_alertes')

    return render(request, 'incubateur/mes_alertes.html', {
        'alertes_challenges': alertes_challenges,
        'alertes_projets': alertes_projets
    })
# --- VUES CHALLENGES ENTREPRISES ---
# incubateur/views.py
from django.db.models import Q
from django.contrib import messages
from .models import ChallengeSearchAlert, ChallengeEntreprise
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import ProjetInnovation, ChallengeEntreprise, ParticipationChallenge

@login_required
def detail_projet(request, slug):
    # On utilise le slug pour une URL propre (ex: /projets/mon-super-projet-x89s)
    projet = get_object_or_404(ProjetInnovation, slug=slug)
    
    # 1. Compteur de Vues (Incrémentation intelligente)
    # On utilise la session pour éviter de compter +1 si je rafraichis la page
    session_key = f'viewed_project_{projet.id}'
    if not request.session.get(session_key, False):
        projet.vues += 1
        projet.save(update_fields=['vues'])
        request.session[session_key] = True

    # 2. Vérifier si l'utilisateur a liké
    a_like = request.user.profile in projet.likes.all()

    return render(request, 'incubateur/detail_projet.html', {
        'projet': projet,
        'a_like': a_like
    })

@login_required
def detail_challenge(request, pk):
    challenge = get_object_or_404(ChallengeEntreprise, pk=pk)
    
    # Vérifier si l'étudiant a déjà participé
    deja_participe = False
    if request.user.profile.role == 'student':
        deja_participe = ParticipationChallenge.objects.filter(
            challenge=challenge, 
            candidat=request.user.profile
        ).exists()

    return render(request, 'incubateur/detail_challenge.html', {
        'challenge': challenge,
        'deja_participe': deja_participe
    })

from django.db import IntegrityError

@login_required
def soumettre_solution(request, pk):
    challenge = get_object_or_404(ChallengeEntreprise, pk=pk)
    profile = request.user.profile

    # 1. Vérification du rôle (Sécurité)
    if profile.role != 'student':
        messages.error(request, "Seuls les étudiants peuvent participer.")
        return redirect('detail_challenge', pk=pk)

    # 2. Vérification Date Limite
    from django.utils import timezone
    if challenge.date_limite < timezone.now():
        messages.error(request, "Dommage, ce challenge est clôturé. ⏳")
        return redirect('detail_challenge', pk=pk)

    # 3. Vérification Doublon (Préventif)
    if ParticipationChallenge.objects.filter(challenge=challenge, candidat=profile).exists():
        messages.warning(request, "Vous avez déjà envoyé une solution pour ce challenge.")
        return redirect('detail_challenge', pk=pk)

    if request.method == 'POST':
        form = ParticipationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                participation = form.save(commit=False)
                participation.candidat = profile
                participation.challenge = challenge
                participation.save()
                
                # Notification de succès
                messages.success(request, f"Bravo ! Votre solution pour '{challenge.titre}' a été envoyée. 🚀")
                
                # Optionnel : Envoyer un mail de confirmation à l'étudiant ici
                envoyer_email_confirmation_soumission(participation, request)
                
                return redirect('detail_challenge', pk=pk)
            
            except IntegrityError:
                # Filet de sécurité si la vérification préventive échoue (double clic rapide)
                messages.warning(request, "Une solution est déjà enregistrée.")
                return redirect('detail_challenge', pk=pk)
    else:
        form = ParticipationForm()

    return render(request, 'incubateur/soumettre_solution.html', {
        'form': form, 
        'challenge': challenge
    })


from .forms import ChallengeForm  # Assure-toi d'importer le nouveau form

@login_required
def creer_challenge(request):
    profile = request.user.profile

    # 1. Sécurité : Seules les entreprises peuvent créer un challenge
    if profile.role != 'company':
        messages.error(request, "Espace réservé aux entreprises partenaires.")
        return redirect('home')

    # 2. Vérification administrative (Optionnel mais recommandé)
    # Si tu veux empêcher une entreprise non vérifiée de poster
    if not profile.company_verified:
        messages.warning(request, "Votre compte entreprise doit être vérifié par l'équipe CampusHub avant de publier un challenge.")
        return redirect('dashboard') # ou accueil

    from accounts.services import UsageManager
    from django.urls import reverse

    # 3. Vérification du quota
    if not UsageManager.is_action_allowed(request.user, 'challenge_publication'):
        messages.warning(request, "Quota de publication de challenges atteint pour votre plan actuel.")
        return redirect(f"{reverse('subscription_plans')}")

    if request.method == 'POST':
        form = ChallengeForm(request.POST, request.FILES)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.entreprise = profile # On lie le challenge à l'entreprise connectée
            challenge.save()
            
            # 4. Incrémenter le quota
            UsageManager.increment_usage(request.user, 'challenge_publication')
            
            messages.success(request, "Votre challenge est en ligne ! Les talents vont bientôt postuler. 🚀")
            return redirect('detail_challenge', pk=challenge.pk)
    else:
        form = ChallengeForm()

    return render(request, 'incubateur/creer_challenge.html', {'form': form})


        
import zipfile
import os
from django.http import HttpResponse
from django.utils.text import slugify
from django.contrib import messages


from .utils import *
import zipfile
import io
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Count, Q
# Assure-toi d'importer tes modèles
from .utils import envoyer_notification_resultat

@login_required
def gerer_soumissions(request, pk):
    # Optimisation 1 : select_related pour éviter 1 requête par candidat
    challenge = get_object_or_404(
        ChallengeEntreprise.objects.select_related('entreprise__user'), 
        pk=pk
    )
    profile = request.user.profile

    # 1. SÉCURITÉ
    if profile.role != 'company' or challenge.entreprise != profile:
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    # 2. GESTION DES ACTIONS (POST)
    if request.method == 'POST':
        action_type = request.POST.get('action_type') # 'decision' ou 'download_all'

        # --- FONCTIONNALITÉ 1 : TÉLÉCHARGEMENT ZIP ---

# ... (ton début de vue) ...

        # --- FONCTIONNALITÉ 1 : TÉLÉCHARGEMENT ZIP ---
        if action_type == 'download_all':
            # On récupère toutes les participations avec un fichier
            participations_with_files = challenge.participationchallenge_set.exclude(fichier_rendu='')
            
            if not participations_with_files.exists():
                messages.warning(request, "Aucun fichier à télécharger pour ce challenge.")
                return redirect('gerer_soumissions', pk=pk)

            # Création du buffer en mémoire
            zip_buffer = io.BytesIO()
            
            # Utilisation de ZIP_DEFLATED pour compresser les fichiers (réduit la taille)
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for p in participations_with_files:
                    try:
                        # On récupère le nom/pseudo de l'étudiant
                        nom_etudiant = p.candidat.full_name or p.candidat.user.username
                        
                        # 1. On nettoie le nom pour éviter les bugs d'encodage dans le ZIP
                        # Ex: "Hélène & Maïa" devient "helene-maia"
                        clean_name = slugify(nom_etudiant)
                        
                        # 2. On récupère la vraie extension du fichier (ex: .pdf, .docx)
                        _, ext = os.path.splitext(p.fichier_rendu.name)
                        
                        # Nom final dans le ZIP : "jean-dupont_42.pdf"
                        filename_in_zip = f"{clean_name}_{p.id}{ext}"
                        
                        # 3. IMPORTANT : Il faut ouvrir le fichier en mode binaire ('rb')
                        with p.fichier_rendu.open('rb') as f:
                            zip_file.writestr(filename_in_zip, f.read())
                            
                    except FileNotFoundError:
                        # Si le fichier est en base de données mais supprimé du disque
                        print(f"Fichier manquant pour la participation ID {p.id}")
                    except Exception as e:
                        print(f"Erreur lors de l'ajout au ZIP (ID {p.id}): {e}")
            
            # Finalisation du ZIP
            zip_buffer.seek(0)
            
            # Nom du fichier ZIP final téléchargé par l'entreprise
            zip_filename = f"Solutions_{slugify(challenge.titre)[:20]}_{pk}.zip"
            
            response = HttpResponse(zip_buffer, content_type="application/zip")
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response
        # --- GESTION DÉCISION (VALIDER / REFUSER) ---
        elif action_type == 'decision':
            participation_id = request.POST.get('participation_id')
            decision = request.POST.get('decision') # 'accept' ou 'reject'
            feedback = request.POST.get('feedback')
            
            participation = get_object_or_404(ParticipationChallenge, id=participation_id, challenge=challenge)
            
            # Utilisation de transaction.atomic pour garantir que tout se fait ou rien
            with transaction.atomic():
                if decision == 'accept':
                    participation.est_vainqueur = True
                    participation.feedback_entreprise = feedback
                    participation.save()

                    # Création du Chat (Logique existante optimisée)
                    try:
                        conversation, created = Conversation.objects.get_or_create(
                            participation=participation,
                            defaults={
                                'student': participation.candidat.user,
                                'company': challenge.entreprise.user
                            }
                        )
                        # Si on vient de créer ou si elle existe, on s'assure que les participants sont là
                        conversation.participants.add(participation.candidat.user, challenge.entreprise.user)

                        # Message système (seulement si nouvelle validation)
                        if created or not conversation.messages.exists():
                            msg_intro = f"""
                            🤖 [Système] : Félicitations ! Solution validée pour "{challenge.titre}".
                            Un canal est ouvert pour discuter de la récompense : {challenge.recompense}.
                            """
                            Message.objects.create(
                                conversation=conversation,
                                sender=request.user,
                                text=msg_intro,
                                msg_type="systeme"
                            )
                            conversation.updated_at = timezone.now()
                            conversation.save()

                        messages.success(request, f"Solution validée ! Redirection vers le chat...")
                        envoyer_notification_resultat(participation, 'accepted', feedback)
                        return redirect('messaging_conversation', pk=conversation.pk)

                    except Exception as e:
                        # En prod, on log l'erreur mais on ne bloque pas l'utilisateur
                        print(f"ERREUR CRITIQUE CHAT: {e}")
                        messages.warning(request, "Validé, mais erreur d'ouverture du chat.")

                elif decision == 'reject':
                    participation.est_vainqueur = False
                    participation.feedback_entreprise = feedback
                    participation.save()
                    messages.info(request, "Candidature refusée et feedback envoyé.")
                    envoyer_notification_resultat(participation, 'rejected', feedback)

            return redirect('gerer_soumissions', pk=pk)

    # 3. FILTRES & TRI (GET)
    filtre = request.GET.get('filtre', 'tous') # tous, winners, pending
    
    # Optimisation SQL : on charge tout d'un coup
    soumissions = challenge.participationchallenge_set.select_related('candidat__user').all()

    # Application des filtres
    if filtre == 'winners':
        soumissions = soumissions.filter(est_vainqueur=True)
    elif filtre == 'pending':
        soumissions = soumissions.filter(est_vainqueur=False, feedback_entreprise__isnull=True)
    
    # Tri par défaut
    soumissions = soumissions.order_by('-est_vainqueur', '-date_soumission')

    # 4. STATISTIQUES (Dashboarding rapide)
    stats = {
        'total': soumissions.count(),
        'gagnants': soumissions.filter(est_vainqueur=True).count(),
        'en_attente': soumissions.filter(est_vainqueur=False, feedback_entreprise__isnull=True).count()
    }

    return render(request, 'incubateur/gerer_soumissions.html', {
        'challenge': challenge,
        'soumissions': soumissions,
        'stats': stats,
        'current_filter': filtre,
        'blind_mode': request.GET.get('blind_mode') == 'on' # Feature recrutement sans biais
    })
    
    
from django.utils import timezone

@login_required
def confirmer_recompense(request, pk):
    participation = get_object_or_404(ParticipationChallenge, pk=pk)
    
    # Sécurité : Seul le candidat vainqueur peut accéder
    if request.user.profile != participation.candidat or not participation.est_vainqueur:
        messages.error(request, "Action non autorisée.")
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            # 1. L'étudiant confirme
            participation.statut_recompense = 'RECEIVED'
            participation.date_confirmation_etudiant = timezone.now()
            participation.save()
            
            # 2. ON RÉCOMPENSE L'ENTREPRISE (Augmentation du Trust Score)
            entreprise_profile = participation.challenge.entreprise
            entreprise_profile.trust_score += 10 # Bonus confiance
            entreprise_profile.save()
            
            messages.success(request, "Merci ! La transaction est close et l'entreprise a été notée positivement.")
            
        elif action == 'dispute':
            motif = request.POST.get('motif_litige')
            
            # 1. L'étudiant signale un problème
            participation.statut_recompense = 'DISPUTE'
            participation.note_litige = motif
            participation.save()
            
            # 2. ON PUNIT L'ENTREPRISE (Baisse temporaire ou alerte Admin)
            entreprise_profile = participation.challenge.entreprise
            entreprise_profile.trust_score -= 5 # Pénalité immédiate (ou attendre enquête admin)
            entreprise_profile.save()
            
            # 3. Alerte Admin (Email)
            # --- UTILISATION DE LA NOUVELLE FONCTION ---
            message_alerte = f"""
            LITIGE DÉCLARÉ SUR UN CHALLENGE
            
            Étudiant : {participation.candidat.full_name} ({participation.candidat.user.email})
            Entreprise : {entreprise_profile.company_name}
            Challenge : {participation.challenge.titre}
            
            Motif du litige :
            "{motif}"
            
            Action requise : Vérifier les échanges et contacter l'entreprise.
            """
            
            send_mail_to_admin(message_alerte)
            messages.warning(request, "Le litige a été ouvert. L'équipe CampusHub va enquêter.")

    return redirect('dashboard') # Ou page détail challenge





# incubateur/views.py
import qrcode
import io
import base64
from django.urls import reverse
from .models import ProjetUpdate
from .forms import ProjetUpdateForm

@login_required
def ajouter_actualite(request, slug):
    projet = get_object_or_404(ProjetInnovation, slug=slug)
    
    # Sécurité : Seul le porteur peut poster
    if request.user.profile != projet.porteur:
        messages.error(request, "Vous n'êtes pas le porteur de ce projet.")
        return redirect('detail_projet', slug=slug)

    if request.method == 'POST':
        form = ProjetUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.projet = projet
            update.save()
            messages.success(request, "Actualité publiée sur le blog du projet ! 🚀")
            return redirect('detail_projet', slug=slug)
    else:
        form = ProjetUpdateForm()

    return render(request, 'incubateur/ajouter_actualite.html', {
        'form': form, 'projet': projet
    })
    
import qrcode
import io
import base64
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from .models import ProjetInnovation
import qrcode
import io
import base64
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from .models import ProjetInnovation

def generer_affiche_qr(request, slug):
    """
    Génère une page HTML imprimable (A4) pour un projet spécifique.
    Inclut un QR Code dynamique et permet de choisir parmi 15 styles visuels.
    """
    # 1. Récupération du projet
    projet = get_object_or_404(ProjetInnovation, slug=slug)
    
    # 2. Récupération du style choisi dans l'URL (par défaut 'moderne')
    style_choisi = request.GET.get('style', 'moderne')

    # 3. Définition des 15 Thèmes (Code CSS, Label Affiché)
    # Cette liste est passée au template pour générer le menu de choix
    themes = [
        ('moderne', '⚡ Moderne (Tech)'),
        ('corporate', '🏢 Corporate (Pro)'),
        ('startup', '🚀 Startup (Gradient)'),
        ('creative', '🎨 Créatif (Bold)'),
        ('minimal', '🌿 Minimal (Épuré)'),
        ('academic', '🎓 Académique (Sérieux)'),
        ('industrial', '🚧 Industriel (BTP)'),
        ('nature', '🍃 Nature (Bio)'),
        ('cyberpunk', '👾 Cyberpunk (Geek)'),
        ('luxury', '💎 Luxe (Prestige)'),
        ('newspaper', '📰 Journal (Rétro)'),
        ('swiss', '🇨🇭 Suisse (Grid)'),
        ('blueprint', '📐 Architecte (Plan)'),
        ('social', '🧡 Social (Warm)'),
        ('retro', '📺 Vintage (Sepia)'),
    ]

    # 4. Construction de l'URL absolue vers la page détail du projet
    # Ex: https://campushub.cm/incubation/projets/mon-super-projet/
    project_url = request.build_absolute_uri(reverse('detail_projet', args=[slug]))
    
    # 5. Génération du QR Code Haute Qualité
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # H = Haute tolérance (30% de dégâts acceptables)
        box_size=10, # Taille des pixels (plus grand = meilleure qualité d'impression)
        border=2,
    )
    qr.add_data(project_url)
    qr.make(fit=True)
    
    # On génère l'image en Noir & Blanc (Le CSS se chargera des couleurs/inversions)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 6. Conversion en Base64 pour l'intégrer directement dans le HTML sans fichier temporaire
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    # 7. Rendu du template
    return render(request, 'incubateur/affiche_projet.html', {
        'projet': projet,
        'qr_code_base64': img_str,   # L'image du code
        'project_url': project_url,  # L'URL texte (au cas où)
        'style': style_choisi,       # Le style actif
        'themes_list': themes        # La liste pour le menu
    })
# def generer_affiche_qr(request, slug):
#     """
#     Génère une page HTML imprimable avec un QR Code
#     pointant vers le détail du projet.
#     """
#     projet = get_object_or_404(ProjetInnovation, slug=slug)
    
#     # 1. Créer l'URL absolue vers le projet (http://campushub.../projet/slug)
#     project_url = request.build_absolute_uri(reverse('detail_projet', args=[slug]))
    
#     # 2. Générer le QR Code
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_H, # Haute correction d'erreur
#         box_size=10,
#         border=4,
#     )
#     qr.add_data(project_url)
#     qr.make(fit=True)
    
#     # 3. Convertir en image base64 pour l'afficher dans le HTML sans sauvegarder
#     img = qr.make_image(fill_color="black", back_color="white")
#     buffer = io.BytesIO()
#     img.save(buffer, format="PNG")
#     img_str = base64.b64encode(buffer.getvalue()).decode()
    
#     return render(request, 'incubateur/affiche_projet.html', {
#         'projet': projet,
#         'qr_code_base64': img_str,
#         'project_url': project_url
#     })
    
    
    
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ProjetInnovation  # Vérifie bien le nom de ton modèle

@login_required
@require_POST
def toggle_like_projet(request, slug):
    try:
        # 1. Récupérer le projet ou renvoyer 404
        projet = get_object_or_404(ProjetInnovation, slug=slug)
        profile = request.user.profile
        
        # 2. Logique de bascule (Toggle)
        # On utilise .all() pour vérifier la présence du profil dans les likes
        if profile in projet.likes.all():
            projet.likes.remove(profile)
            liked = False
        else:
            projet.likes.add(profile)
            liked = True
            
        # 3. Réponse JSON propre
        # On utilise .count() directement sur le manager pour éviter les erreurs d'attributs
        return JsonResponse({
            'status': 'success',
            'liked': liked,
            'count': projet.likes.count()
        })

    except Exception as e:
        # En cas d'erreur (ex: profil manquant), on renvoie l'erreur en JSON
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
    
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import ProjetInnovation, ChallengeEntreprise
from .forms import ProjetForm, ChallengeForm
from .utils import notifier_modification_challenge, notifier_suppression_challenge # Importe tes fonctions

# =========================================================
# GESTION PROJETS (Modification / Suppression)
# =========================================================

@login_required
def modifier_projet(request, slug):
    projet = get_object_or_404(ProjetInnovation, slug=slug)

    # 1. SÉCURITÉ : Seul le porteur peut modifier
    if request.user.profile != projet.porteur:
        messages.error(request, "Vous ne pouvez pas modifier un projet qui n'est pas le vôtre.")
        return redirect('detail_projet', slug=slug)

    if request.method == 'POST':
        form = ProjetForm(request.POST, request.FILES, instance=projet)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre projet a été mis à jour avec succès ! 🚀")
            return redirect('detail_projet', slug=slug)
    else:
        form = ProjetForm(instance=projet)

    return render(request, 'incubateur/modifier_projet.html', {
        'form': form, 'projet': projet
    })

@login_required
def supprimer_projet(request, slug):
    projet = get_object_or_404(ProjetInnovation, slug=slug)

    # 1. SÉCURITÉ
    if request.user.profile != projet.porteur:
        messages.error(request, "Action non autorisée.")
        return redirect('detail_projet', slug=slug)

    if request.method == 'POST':
        # Pas d'email complexe ici, car c'est souvent l'étudiant seul
        # Mais si il y a une équipe, on pourrait les notifier ici
        titre_backup = projet.titre
        projet.delete()
        messages.success(request, f"Le projet '{titre_backup}' a été supprimé définitivement.")
        return redirect('liste_projets')

    return render(request, 'incubateur/confirmer_suppression.html', {
        'objet': projet, 'type': 'projet'
    })


# =========================================================
# GESTION CHALLENGES (Modification / Suppression)
# =========================================================

@login_required
def modifier_challenge(request, pk):
    challenge = get_object_or_404(ChallengeEntreprise, pk=pk)

    # 1. SÉCURITÉ : Seule l'entreprise propriétaire peut modifier
    if request.user.profile != challenge.entreprise:
        messages.error(request, "Accès refusé.")
        return redirect('detail_challenge', pk=pk)

    # On garde l'ancienne date pour comparer
    ancienne_date = challenge.date_limite

    if request.method == 'POST':
        form = ChallengeForm(request.POST, request.FILES, instance=challenge)
        if form.is_valid():
            challenge_modifie = form.save()
            
            # 2. LOGIQUE EMAIL : Si la date change, on prévient les candidats
            if challenge_modifie.date_limite != ancienne_date:
                notifier_modification_challenge(challenge_modifie, modifications_importantes=True)
                messages.info(request, "Les candidats ont été notifiés du changement de date.")

            messages.success(request, "Challenge mis à jour.")
            return redirect('detail_challenge', pk=pk)
    else:
        form = ChallengeForm(instance=challenge)

    return render(request, 'incubateur/modifier_challenge.html', {
        'form': form, 'challenge': challenge
    })

@login_required
def supprimer_challenge(request, pk):
    challenge = get_object_or_404(ChallengeEntreprise, pk=pk)

    # 1. SÉCURITÉ
    if request.user.profile != challenge.entreprise:
        messages.error(request, "Accès refusé.")
        return redirect('detail_challenge', pk=pk)

    if request.method == 'POST':
        # 2. LOGIQUE EMAIL : On prévient tout le monde AVANT de supprimer
        # (Sinon on perd l'accès à la liste des participants)
        notifier_suppression_challenge(challenge)
        
        titre_backup = challenge.titre
        challenge.delete()
        
        messages.success(request, f"Le challenge '{titre_backup}' a été clôturé et supprimé. Les participants ont été notifiés.")
        return redirect('liste_challenges')

    return render(request, 'incubateur/confirmer_suppression.html', {
        'objet': challenge, 'type': 'challenge'
    })
    
    
    
from django.shortcuts import render
from django.db.models import Q
from .models import EtudiantTalent

def liste_talents(request):
    query = request.GET.get('q')
    # On récupère les talents triés par moyenne générale décroissante
    talents = EtudiantTalent.objects.all().order_by('-moyenne_generale')

    if query:
        talents = talents.filter(
            Q(noms_prenoms__icontains=query) |
            Q(filiere__icontains=query) |
            Q(competences__nom__icontains=query)
        ).distinct()

    return render(request, 'liste_talents.html', {'talents': talents, 'query': query})




import os
from groq import Groq
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import InterviewSession, ChatMessage
from .forms import InterviewSetupForm

# --- CONFIGURATION CLIENT GROQ ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY_COACH", "") 
groq_client = Groq(api_key=GROQ_API_KEY)

@login_required
def start_coach(request):
    from accounts.services import UsageManager
    from django.urls import reverse

    if not UsageManager.is_action_allowed(request.user, 'interview_ia'):
        messages.warning(request, "Quota d'interviews IA atteint.")
        return redirect(f"{reverse('payments:initiate_payment')}?action=interview_ia&amount=500")

    if request.method == 'POST':
        form = InterviewSetupForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save()
            
            # Message d'accueil (géré localement pour économiser l'IA)
            welcome_msg = f"Bonjour ! Je suis ton coach IA. Nous simulons un entretien pour : {session.target_role} (Niveau {session.get_difficulty_display()}). Présente-toi brièvement pour commencer."
            ChatMessage.objects.create(session=session, sender='ai', content=welcome_msg)
            
            return redirect('interview_room', session_id=session.id)
    else:
        form = InterviewSetupForm()
    
    return render(request, 'training/start_coach.html', {'form': form})

def interview_room(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    return render(request, 'training/interview_room.html', {'session': session})

# Dans training/views.py

# ... imports ...
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import InterviewSession, ChatMessage

# Assure-toi que ton client est initialisé plus haut dans le fichier

def api_chat_response(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        user_message = request.POST.get('message', '') 
        uploaded_file = request.FILES.get('document') 
        
        # 1. Sauvegarder le message de l'étudiant
        content_to_log = user_message
        if uploaded_file:
            content_to_log += f" [Fichier joint : {uploaded_file.name}]"
            
        ChatMessage.objects.create(session=session, sender='user', content=content_to_log)
        
        # 2. Préparer le message ACTUEL (Texte + Fichier)
        current_parts = []
        
        if user_message:
            current_parts.append(user_message)
            
        if uploaded_file:
            # Pour l'instant on se limite au texte si on n'a pas configuré le File API complexe
            # car genai.upload_file nécessite un fichier sur le disque.
            content_to_log += f" [Fichier joint ignorer temporairement dans le chat IA]"

        # 3. Construction de l'historique OPTIMISÉE
        history_items = []
        
        # On récupère seulement les 15 derniers messages
        last_msgs = session.messages.order_by('-timestamp')[:15]
        previous_msgs = reversed(last_msgs)
        
        for msg in previous_msgs:
            if msg.content == content_to_log and msg.sender == 'user': 
                continue
                
            role = "model" if msg.sender == 'ai' else "user"
            history_items.append({"role": role, "parts": [msg.content]})

        # 4. Prompt contextuel
        messages = [
            {"role": "system", "content": context_prompt}
        ]
        
        # Ajouter l'historique
        for item in history_items:
            messages.append({"role": item["role"], "content": item["parts"][0]})
            
        # Ajouter le message actuel
        messages.append({"role": "user", "content": user_message})

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.8,
            )
            ai_reply = chat_completion.choices[0].message.content
            
            ChatMessage.objects.create(session=session, sender='ai', content=ai_reply)
            
            return JsonResponse({'status': 'success', 'reply': ai_reply})
            
        except Exception as e:
            print(f"Erreur Gemini : {str(e)}") 
            return JsonResponse({'status': 'error', 'message': "Erreur technique lors de l'analyse."})
            
    return JsonResponse({'status': 'error'}, status=400)
# from google import genai
# import os

# # Remplace par ta vraie clé API
# client = genai.Client(api_key="AIzaSyD79rZoiNx7_3tX8d8retOddf2SL2edT-w")

# print("--- RECHERCHE DES MODÈLES ---")

# try:
#     # On parcourt simplement la liste sans filtrer les attributs complexes
#     for model in client.models.list():
#         print(f"Modèle trouvé : {model.name}")
        
# except Exception as e:
#     print(f"Erreur : {e}")


def end_interview_and_report(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    # On récupère tout l'historique en texte
    conversation_text = ""
    for msg in session.messages.all():
        sender = "Recruteur" if msg.sender == 'ai' else "Candidat"
        conversation_text += f"{sender}: {msg.content}\n"

    # Prompt d'analyse
    prompt_analyse = f"""
    Analyse l'entretien d'embauche suivant :
    {conversation_text}

    Génère un rapport JSON strict avec ces clés :
    1. "score": Note sur 100.
    2. "points_forts": Liste de 3 points forts.
    3. "points_faibles": Liste de 3 points faibles.
    4. "conseil_principal": Le meilleur conseil pour s'améliorer.
    5. "verdict": "Embauché" ou "Recalé".
    """

    # Appel Groq
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt_analyse,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        report = chat_completion.choices[0].message.content
        
        # Sauvegarde
        session.final_report = report
        session.is_finished = True
        session.save()
        
        # Incrémenter le quota
        from accounts.services import UsageManager
        UsageManager.increment_usage(request.user, 'interview_ia')
        
        return render(request, 'training/report_card.html', {'session': session, 'report': report})
    except:
        return redirect('home') # Gestion d'erreur basique
    
    