from django.urls import path
from . import views, webhooks

app_name = 'payments'

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate_payment'),
    path('success/', views.payment_success, name='payment_success'),
    path('failure/', views.payment_failure, name='payment_failure'),
    
    # Webhooks
    path('webhooks/cinetpay/', webhooks.cinetpay_webhook, name='cinetpay_webhook'),
    path('webhooks/flutterwave/', webhooks.flutterwave_webhook, name='flutterwave_webhook'),
]
