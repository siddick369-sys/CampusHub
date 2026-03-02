import uuid
from decimal import Decimal
from .models import PaymentTransaction, ProviderMetrics, PaymentAuditLog
from .providers.cinetpay import CinetPayProvider
from .providers.flutterwave import FlutterwaveProvider

class PaymentRouterService:
    @staticmethod
    def get_best_provider(payment_method, amount):
        """
        Choisit le meilleur provider selon la méthode, le montant et les metrics.
        """
        # 1. Règles basiques
        if payment_method == 'mobile_money':
            return CinetPayProvider()
        
        if payment_method == 'card':
            return FlutterwaveProvider()

        # 2. Smart Routing pour montants élevés (> 10000)
        if amount > 10000:
            # Ici on pourrait comparer les success_rate en DB dans ProviderMetrics
            return FlutterwaveProvider() # Flutterwave souvent plus stable sur gros montants cartes

        # Par défaut
        return CinetPayProvider()

    @staticmethod
    def create_transaction(user, amount, method, action_type=None, plan_id=None):
        """Crée une transaction en base de données avant de switcher sur le provider."""
        internal_ref = f"CH-{uuid.uuid4().hex[:12].upper()}"
        
        transaction = PaymentTransaction.objects.create(
            user=user,
            amount=Decimal(str(amount)),
            payment_method=method,
            internal_reference=internal_ref,
            action_type=action_type,
            plan_id=plan_id,
            status='pending'
        )
        
        provider = PaymentRouterService.get_best_provider(method, amount)
        transaction.provider = provider.__class__.__name__
        transaction.save(update_fields=['provider'])
        
        return transaction, provider
