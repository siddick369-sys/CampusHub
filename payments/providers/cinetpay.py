import hashlib
import json
import requests
from django.conf import settings
from .base import PaymentProviderInterface

class CinetPayProvider(PaymentProviderInterface):
    def __init__(self):
        self.site_id = getattr(settings, 'CINETPAY_SITE_ID', '123456')
        self.api_key = getattr(settings, 'CINETPAY_API_KEY', 'apikey')
        self.base_url = "https://api-checkout.cinetpay.com/v2/payment"

    def create_payment(self, transaction, **kwargs):
        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction.internal_reference,
            "amount": int(transaction.amount),
            "currency": transaction.currency,
            "alternative_currency": "",
            "description": f"CampusHub - {transaction.user.username}",
            "customer_id": str(transaction.user.id),
            "customer_name": transaction.user.first_name or transaction.user.username,
            "customer_surname": transaction.user.last_name or "",
            "customer_email": transaction.user.email,
            "customer_phone_number": getattr(transaction.user.profile, 'phone', ''),
            "customer_address": getattr(transaction.user.profile, 'address', ''),
            "customer_city": getattr(transaction.user.profile, 'city', ''),
            "customer_country": "CM", # Cameroon
            "customer_state": "",
            "customer_zip_code": "",
            "notify_url": settings.SITE_BASE_URL + "/payments/webhooks/cinetpay/",
            "return_url": settings.SITE_BASE_URL + "/payments/success/",
            "channels": "ALL",
            "metadata": json.dumps({"transaction_id": transaction.id}),
            "lang": "fr"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            data = response.json()
            if data.get('code') == '201':
                return {"checkout_url": data['data']['payment_url'], "external_id": data['data']['payment_token']}
            return {"error": data.get('message', 'Erreur CinetPay')}
        except Exception as e:
            return {"error": str(e)}

    def verify_webhook(self, payload, signature, **kwargs):
        # La validation CinetPay se fait souvent via un hash HMAC ou une vérification directe
        # Ici simulation de la logique de signature
        if signature: # Simplification pour le moment
            return "success" if payload.get('code') == '00' else "failed"
        return "invalid_signature"

    def get_transaction_status(self, external_id):
        check_url = "https://api-checkout.cinetpay.com/v2/payment/check"
        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "token": external_id
        }
        try:
            response = requests.post(check_url, json=payload, timeout=10)
            data = response.json()
            return data.get('data', {}).get('status', 'unknown')
        except:
            return "error"

    def refund(self, transaction_id, amount=None):
        return {"error": "Refund not implemented for CinetPay MM"}
