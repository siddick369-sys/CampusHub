from abc import ABC, abstractmethod

class PaymentProviderInterface(ABC):
    @abstractmethod
    def create_payment(self, transaction, **kwargs):
        """Initialise un paiement et retourne l'URL de redirection ou les données de checkout."""
        pass

    @abstractmethod
    def verify_webhook(self, payload, signature, **kwargs):
        """Vérifie l'authenticité d'un webhook et retourne le statut de la transaction."""
        pass

    @abstractmethod
    def get_transaction_status(self, external_id):
        """Interroge l'API du provider pour obtenir le statut actuel."""
        pass

    @abstractmethod
    def refund(self, transaction_id, amount=None):
        """Effectue un remboursement (si supporté)."""
        pass
