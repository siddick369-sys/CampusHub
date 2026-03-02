from django.db import models
from django.conf import settings
from django.utils import timezone

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('success', 'Réussi'),
        ('failed', 'Échoué'),
        ('expired', 'Expiré'),
    ]

    METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte Bancaire'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='XAF')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    provider = models.CharField(max_length=50) # CinetPay, Flutterwave
    external_transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    internal_reference = models.CharField(max_length=100, unique=True) # ID généré pour le suivi interne
    
    # Suivi de l'objet du paiement
    action_type = models.CharField(max_length=50, blank=True, null=True) # cv_ia, interview_ia, etc.
    plan = models.ForeignKey('accounts.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    signature_verified = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.status})"

class PaymentAuditLog(models.Model):
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    provider = models.CharField(max_length=50)
    raw_webhook_payload = models.TextField()
    signature_status = models.CharField(max_length=50)
    validation_result = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ProviderMetrics(models.Model):
    provider_name = models.CharField(max_length=50, unique=True)
    total_transactions = models.PositiveIntegerField(default=0)
    success_rate = models.FloatField(default=0.0)
    avg_response_time = models.FloatField(default=0.0) # en secondes
    failure_rate = models.FloatField(default=0.0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)
    commission_estimated = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Metrics: {self.provider_name}"
