from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from .services import SubscriptionManager

class EmailVerificationRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            profile = getattr(request.user, 'profile', None)
            if profile and not profile.email_verified:
                # Éviter une boucle de redirection infinie
                exempt_urls = [
                    reverse('verify_code'),
                    reverse('resend_code'),
                    reverse('logout'),
                    reverse('login'),
                ]
                # Ajouter les URLs de base si nécessaire
                if request.path not in exempt_urls and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                    return redirect('verify_code')
        
        return self.get_response(request)

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile:
                # 1. Activation automatique du trial à la première connexion
                if not profile.first_login_at:
                    SubscriptionManager.activate_trial(request.user)
                
                # 2. Injection du statut d'abonnement dans la requête pour utilisation facile en template
                sub = getattr(request.user, 'user_subscription', None)
                if sub:
                    sub.check_active() # Vérifie si expiré en temps réel
                    request.subscription = sub
                    
                    # 3. Notification 3 jours avant expiration
                    if sub.is_active and not sub.is_expired:
                        remaining_days = sub.days_remaining() if hasattr(sub, 'days_remaining') else (sub.end_date - timezone.now()).days
                        request.show_expiration_warning = (0 <= remaining_days <= 3)
                else:
                    request.subscription = None
        
        response = self.get_response(request)
        return response