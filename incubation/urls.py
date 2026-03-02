from django.urls import path
from . import views

urlpatterns = [
    # Projets
    path('projets/', views.liste_projets, name='liste_projets'),
    path('projets/nouveau/', views.creer_projet, name='creer_projet'),
    
    # Challenges
    path('challenges/', views.liste_challenges, name='liste_challenges'),
    path('challenges/<int:pk>/', views.detail_challenge, name='detail_challenge'),
    path('challenges/<int:pk>/gestion', views.gerer_soumissions, name='gerer_soumissions'),
    path('challenges/<int:pk>/participer/', views.soumettre_solution, name='soumettre_solution'),

    # ... tes autres urls ...
    path('challenges/nouveau/', views.creer_challenge, name='creer_challenge'),
    path('mes-alertes/', views.mes_alertes, name='mes_alertes'),
    path('talent-iut/', views.liste_talents, name='liste_talents'),
    path('projets/<slug:slug>/actualite/ajouter/', views.ajouter_actualite, name='ajouter_actualite'),
    path('projets/<slug:slug>/affiche/', views.generer_affiche_qr, name='generer_affiche_qr'),
    path('details/projets/<slug:slug>/', views.detail_projet, name='detail_projet'),
    path('projets/<slug:slug>/like/', views.toggle_like_projet, name='toggle_like_projet'),
    path('projets/<slug:slug>/modifier/', views.modifier_projet, name='modifier_projet'),
path('projets/<slug:slug>/supprimer/', views.supprimer_projet, name='supprimer_projet'),

path('challenges/<int:pk>/modifier/', views.modifier_challenge, name='modifier_challenge'),
path('challenges/<int:pk>/supprimer/', views.supprimer_challenge, name='supprimer_challenge'),


    path('coach/', views.start_coach, name='start_coach'),
    path('coach/room/<int:session_id>/', views.interview_room, name='interview_room'),
    path('coach/api/<int:session_id>/', views.api_chat_response, name='api_chat_response'),
    path('coach/report/<int:session_id>/', views.end_interview_and_report, name='end_interview'),


]