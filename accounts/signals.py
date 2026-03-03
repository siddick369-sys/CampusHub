from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Subscription, SubscriptionPlan

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_default_subscription(sender, instance, created, **kwargs):
    """Assigne le plan par défaut correspondant au rôle de l'utilisateur à sa création."""
    if created:
        profile = getattr(instance, 'profile', None)
        role = profile.role if profile else 'student'
        
        default_plan = SubscriptionPlan.objects.filter(role_target=role, is_default=True).first()
        if default_plan:
            Subscription.objects.get_or_create(
                user=instance,
                defaults={
                    "plan": default_plan,
                    "start_date": timezone.now(),
                    "end_date": timezone.now() + timedelta(days=365),
                    "is_active": True
                }
            )

@receiver(post_save, sender=Subscription)
def auto_disable_expired_subscription(sender, instance, **kwargs):
    """Désactive l’abonnement unifié si la date de fin est dépassée."""
    if instance.end_date and timezone.now() > instance.end_date and instance.is_active:
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        
        
        
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    Crée un profil automatiquement après la création d’un utilisateur.
    """
    if created:
        Profile.objects.create(user=instance)
    # Suppression du else pour éviter les crashs de validation lors des updates (ex: login)