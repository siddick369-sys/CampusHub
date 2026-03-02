"""
URL configuration for CampuHub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf.urls.static import static

from stages.models import PlatformReview
from . import views # Adapte selon ton app


# views.py
from django.shortcuts import render

def home_view(request):
    user_role = None
    
    if request.user.is_authenticated:
        user_role = getattr(request.user.profile, "role", None)
    return render(request, "home.html", {
        "user_role": user_role
        })

# apps/accounts/views.py (ou autre app principale)
from django.shortcuts import render

def about_view(request):
    """
    Vue de la page À propos — affiche la présentation du projet CampusHub,
    son objectif et son équipe.
    """
    # Tu pourras plus tard ajouter une récupération d’équipe depuis la base de données
    team_members = [
        {"name": "Aboubakar Ibrahim Siddick", "role": "Developpeur frontend+backend", "image": "images/team1.jpg"},
        {"name": "Acko'o Suzanne", "role": "Développeur frontend", "image": "images/team2.png"},
        {"name": "Tala Maryam Ousmanou", "role": "UI/UX Designer", "image": "images/team3.png"},
    ]
    return render(request, "pages/about.html", {"team_members": team_members})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),

    # ... tes autres urls ...
    
    # API Navigation Vocale
    path('api/voice-navigation/', views.voice_navigation_api, name='voice_navigation_api'),

    path('about/', about_view, name='about'),
    path('accounts/', include('accounts.urls')),
    path('payments/', include('payments.urls')),
    path('stages/', include('stages.urls')),
    path('services/', include('services.urls')),
    path('ai-assistant/', include('ai_assistant.urls')),
    path('orientation/', include('orientation.urls')),
    path('incubation/', include('incubation.urls')),
    # urls.py
    # ...
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms/', views.terms_conditions_view, name='terms_conditions'),
    path('legal/', views.legal_notices_view, name='legal_notices'),
    path('help/', views.how_it_works_view, name='how_it_works'),

    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
    
    

from django.conf.urls import handler404, handler500, handler403, handler400
from django.shortcuts import render

# --- VUES D'ERREUR PERSONNALISÉES ---

def custom_page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_server_error(request):
    return render(request, 'errors/500.html', status=500)

def custom_permission_denied(request, exception):
    return render(request, 'errors/403.html', status=403)

def custom_bad_request(request, exception):
    return render(request, 'errors/400.html', status=400)

# --- ASSIGNATION DES HANDLERS ---
handler404 = custom_page_not_found
handler500 = custom_server_error
handler403 = custom_permission_denied
handler400 = custom_bad_request