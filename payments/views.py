from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .services import PaymentRouterService
from .models import PaymentTransaction

@login_required
def initiate_payment(request):
    """Vue pour initier un paiement Pay-per-Action."""
    amount = request.GET.get('amount', 500)
    method = request.GET.get('method', 'mobile_money')
    action_type = request.GET.get('action')
    plan_id = request.GET.get('plan_id')

    transaction, provider = PaymentRouterService.create_transaction(
        user=request.user,
        amount=amount,
        method=method,
        action_type=action_type,
        plan_id=plan_id
    )

    result = provider.create_payment(transaction)
    
    if "checkout_url" in result:
        transaction.external_transaction_id = result['external_id']
        transaction.save(update_fields=['external_transaction_id'])
        return redirect(result['checkout_url'])
    else:
        transaction.status = 'failed'
        transaction.failure_reason = result.get('error')
        transaction.save()
        return render(request, 'payments/error.html', {'error': result.get('error')})

@login_required
def payment_success(request):
    return render(request, 'payments/success.html')

@login_required
def payment_failure(request):
    return render(request, 'payments/error.html')
