import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from payments.models import PaymentTransaction, PaymentAuditLog
from .services import PaymentRouterService
from accounts.services import UsageManager

@csrf_exempt
@require_POST
def cinetpay_webhook(request):
    """Réception des notifications de paiement CinetPay."""
    payload = request.POST.dict()
    signature = request.headers.get('x-cinetpay-signature')
    
    # Audit Log
    PaymentAuditLog.objects.create(
        provider='CinetPay',
        raw_webhook_payload=json.dumps(payload),
        signature_status='received',
        validation_result='pending',
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # Simulation de validation (à renforcer avec le provider)
    internal_ref = payload.get('cpm_trans_id')
    try:
        transaction = PaymentTransaction.objects.get(internal_reference=internal_ref)
        if payload.get('cpm_result') == '00':
            transaction.status = 'success'
            transaction.validated_at = timezone.now()
            transaction.save()
            # Activer le service ici si besoin (via PaymentManager)
            return HttpResponse("OK")
        else:
            transaction.status = 'failed'
            transaction.save()
            return HttpResponse("FAIL")
    except PaymentTransaction.DoesNotExist:
        return HttpResponse("NOT_FOUND", status=404)

@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    """Réception des notifications de paiement Flutterwave."""
    payload = json.loads(request.body)
    signature = request.headers.get('verif-hash')
    
    PaymentAuditLog.objects.create(
        provider='Flutterwave',
        raw_webhook_payload=request.body.decode('utf-8'),
        signature_status='received',
        ip_address=request.META.get('REMOTE_ADDR')
    )

    internal_ref = payload.get('tx_ref')
    # ... logique similaire ...
    return HttpResponse("OK")
