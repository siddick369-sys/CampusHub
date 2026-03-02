from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # 🔥 nouvelle route pour le code :
    path('verify-code/', views.verify_code_view, name='verify_code'),
    path('resend-code/', views.resend_code_view, name='resend_code'),
    path('profile/delete/', views.delete_profil_view, name='profile_delete'),

    # ...
    path("trust-score/", views.trust_score_dashboard_view, name="trust_score_dashboard"),
    path("trust-score/export/", views.trust_score_export_html_view, name="trust_score_export"),
    path('dashboard/access/', views.dashboard_access_view, name='dashboard_access'),



    # ... autres urls ...

    # 1. Action pour définir le document actif
    path('documents/<int:doc_id>/set-qr/', views.set_qr_document, name='set_qr_document'),

    # 2. L'URL publique scannée par le QR Code (Important : utiliser le username)
    path('c/<str:username>/', views.qr_redirect_view, name='qr_redirect_view'),

    # 3. L'URL qui génère l'image PNG
    path('my-campus-pass.png', views.generate_campus_pass_view, name='generate_campus_pass'),




    # ...

    path(
        "mon-score/export-pdf/",
        views.trust_score_export_pdf_view,
        name="trust_score_export_pdf",
    ),

    path("devenir-prestataire/", views.become_provider_view, name="become_provider"),

    
    path("notifications/services/", views.service_email_settings_view, name="service_email_settings"),
    path("notifications/services/toggle-provider/", views.toggle_service_email_as_provider_view, name="toggle_service_email_as_provider"),
    path("notifications/services/toggle-client/", views.toggle_service_email_as_client_view, name="toggle_service_email_as_client"),

    path("plans/", views.subscription_plans_view, name="subscription_plans"),
    path("subscribe/<int:plan_id>/", views.subscribe_view, name="subscribe"),
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset_form.html'), 
         name='password_reset'),

    # 2. Message "Email envoyé"
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
         name='password_reset_done'),

    # 3. Lien de confirmation (Saisir nouveau mot de passe)
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), 
         name='password_reset_confirm'),

    # 4. Succès "Mot de passe changé"
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
         name='password_reset_complete'),




    path(
        "company/verification/",
        views.company_verification_request_view,
        name="company_verification_request"
    ),

    # ... autres routes ...
    path("success-stories/", views.success_stories_view, name="success_stories"),
    path("update-onboarding-status/", views.update_onboarding_status, name="update_onboarding_status"),
]