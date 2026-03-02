import requests
from django.conf import settings
from .base import PaymentProviderInterface

class FlutterwaveProvider(PaymentProviderInterface):
    def __init__(self):
        self.secret_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', 'FLWSECK-xxxx')
        self.base_url = "https://api.flutterwave.com/v3/payments"

    def create_payment(self, transaction, **kwargs):
        payload = {
            "tx_ref": transaction.internal_reference,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "redirect_url": settings.SITE_BASE_URL + "/payments/success/",
            "payment_options": "card,mobilemoneycambodia", # adapter selon besoins
            "customer": {
                "email": transaction.user.email,
                "phonenumber": getattr(transaction.user.profile, 'phone', ''),
                "name": transaction.user.get_full_name() or transaction.user.username
            },
            "customizations": {
                "title": "CampusHub",
                "description": "Système de monétisation CampusHub",
                "logo": ""
            }
        }
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
            data = response.json()
            if data.get('status') == 'success':
                return {"checkout_url": data['data']['link'], "external_id": str(data['data']['id'])}
            return {"error": data.get('message', 'Erreur Flutterwave')}
        except Exception as e:
            return {"error": str(e)}

    def verify_webhook(self, payload, signature, **kwargs):
        # Vérification Flutterwave via Hash secret dans headers
        secret_hash = getattr(settings, 'FLUTTERWAVE_SECRET_HASH', 'mysupersecret')
        if signature == secret_hash:
            return "success" if payload.get('status') == 'successful' else "failed"
        return "invalid_signature"

    def get_transaction_status(self, external_id):
        url = f"https://api.flutterwave.com/v3/transactions/{external_id}/verify"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            return data.get('data', {}).get('status', 'unknown')
        except:
            return "error"

    def refund(self, transaction_id, amount=None):
        url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/refund"
        # ... logic refund ...
        return {"status": "pending"}
