from django.urls import path
from . import views
from . import cv_views

urlpatterns = [
     path(
    "offers/matching/",
    views.student_matching_offers_view,
    name="student_matching_offers"
),
    path(
    'company/offers/<slug:slug>/status/<str:new_status>/',
    views.company_offer_change_status_view,
    name='company_offer_change_status',
),
    path('avis/', views.reviews_list_view, name='platform_reviews'),

    # Action de soumission du formulaire (POST)
    path('avis/soumettre/', views.submit_platform_review, name='submit_review'),
    
    # Optionnel : Action pour supprimer son propre avis
    path('avis/supprimer/<int:review_id>/', views.delete_review, name='delete_review'),

    # ... tes autres routes ...

    path(
        "notifications/disable-orientation-alerts/",
        views.disable_orientation_alerts_view,
        name="disable_orientation_alerts",
    ),
    path(
    "notifications/enable-orientation-alerts/",
    views.enable_orientation_alerts_view,
    name="enable_orientation_alerts",
),



    # ... tes autres routes ...

    path("student/job-alerts/json/", views.job_alerts_list_api, name="job_alerts_list_api"),
    path("student/job-alerts/<int:alert_id>/delete/", views.delete_job_alert_api, name="delete_job_alert_api"),




    # ... tes autres urls ...

    path("offers/<slug:slug>/save-toggle/", views.toggle_save_offer_view, name="offer_save_toggle"),
    path("student/saved-offers/", views.saved_offers_list_view, name="student_saved_offers"),




    # ... ce que tu as déjà ...

    path("messages/<int:pk>/edit/", views.message_edit_view, name="message_edit"),
    path("messages/<int:pk>/delete/", views.message_delete_view, name="message_delete"),

    path(
    "messages/",
    views.messaging_inbox_view,
    name="messaging_inbox"
),
    path("messages/<int:pk>/archive/", views.messaging_archive_conversation_view, name="messaging_archive"),
    path("messages/<int:pk>/unarchive/", views.messaging_unarchive_conversation_view, name="messaging_unarchive"),
path(
    "messages/<int:pk>/",
    views.messaging_conversation_view,
    name="messaging_conversation"
),


    # ... tes autres routes ...
    path("chat/ping/", views.chat_ping_view, name="chat_ping"),
    path("chat/status/<int:user_id>/", views.chat_status_view, name="chat_status"),

path(
    "messages/<int:pk>/block/",
    views.conversation_block_view,
    name="conversation_block"
),
path(
    "messages/<int:pk>/report/",
    views.conversation_report_view,
    name="conversation_report"
),
    # Étudiant — Offres
    path('offers/', views.offer_list_view, name='offer_list'),
    path('offers/<slug:slug>/', views.offer_detail_view, name='offer_detail'),
    path('offers/<slug:slug>/apply/', views.apply_to_offer_view, name='apply_to_offer'),
    path(
        "offers/<int:pk>/delete/",
        views.stage_offer_delete_view,
        name="stage_offer_delete"
    ),
    path('offers/<slug:slug>/motivation/', views.motivation_letter_template_view, name='motivation_letter_template'),

    # Étudiant — Candidatures
    path('applications/', views.student_applications_view, name='student_applications'),
    # ... autres urls ...
    

    path('applications/<int:pk>/withdraw/', views.withdraw_application_view, name='withdraw_application'),

    # Étudiant — Recommandations & Lettres
    path('recommended/', views.recommended_offers_view, name='recommended_offers'),
    path('recommendation-letter/', views.recommendation_template_view, name='recommendation_template'),

    # Notifications
    path('notifications/', views.notifications_list_view, name='notifications_list'),

    # Entreprise — Offres
    path('company/offers/', views.company_offers_view, name='company_offers'),
    path('test/', views.stages_test_view, name='stages_test'),
    path('company/offers/create/', views.company_offer_create_view, name='company_offer_create'),
    path('company/offers/<slug:slug>/edit/', views.company_offer_edit_view, name='company_offer_edit'),

    # Entreprise — Candidatures reçues
    path('company/offers/<slug:slug>/applications/',
         views.company_offer_applications_view,
         name='company_offer_applications'),
    path("cv/generate/", views.generate_and_save_cv_view, name="student_cv_generate"),

    path('company/applications/<int:pk>/update/',
         views.company_application_update_status_view,
         name='company_application_update'),
    path('application/<slug:slug>/review/', views.submit_company_review, name='submit_company_review'),
    path("application/<int:application_id>/feedback/", views.company_feedback_view, name="company_feedback"),
      path(
    'offers/<slug:slug>/motivation/pdf/',
    views.motivation_letter_pdf_view,
    name='motivation_letter_pdf'),
     
    # liste des candidatures pour une offre
    path(
        "company/offers/<slug:slug>/applications/",
        views.company_offer_applications_view,
        name="company_offer_applications",
    ),
    path("student/dashboard/", views.student_opportunities_dashboard_view, name="student_dashboard"),
    
    
    path(
        "company/dashboard/",
        views.company_dashboard_view,
        name="company_dashboard"
    ),
    # companies/urls.py

    path("plans/", views.company_subscription_plans_view, name="company_subscription_plans"),
    path("subscribe/<int:plan_id>/", views.company_subscribe_view, name="company_subscribe"),


    # ... autres URLs comptes / auth ...

    # 🔹 Page où l’entreprise envoie sa demande de vérification
    

    # 🔹 Page qui montre le statut de vérification (optionnel, mais très utile)
    




    # détail d'une candidature précise


    path("documents/<int:pk>/delete/", views.student_document_delete_view, name="student_document_delete"),
    
    path("documents/", views.student_documents_list_view, name="student_documents_list"),
    path("documents/upload/", views.student_document_upload_view, name="student_document_upload"),
    path("documents/<int:pk>/download/", views.student_document_download_view, name="student_document_download"),

    # ===== CV Generator Pro =====
    path("cv/builder/", cv_views.cv_builder_view, name="cv_builder"),
    path("cv/preview/", cv_views.cv_preview_view, name="cv_preview"),
    path("cv/download/", cv_views.cv_download_pdf_view, name="cv_download_pdf"),
    path("cv/save/", cv_views.cv_save_draft_api, name="cv_save_draft"),
    path("cv/ai-enhance/", cv_views.cv_ai_enhance_api, name="cv_ai_enhance"),
    path("cv/score/", cv_views.cv_score_api, name="cv_score_api"),
    path("cv/duplicate/", cv_views.cv_duplicate_view, name="cv_duplicate"),
    path("cv/switch/<uuid:cv_id>/", cv_views.cv_switch_view, name="cv_switch"),
    path("cv/new/", cv_views.cv_new_view, name="cv_new"),
    path("cv/delete/", cv_views.cv_delete_view, name="cv_delete"),
    path("cv/versions/", cv_views.cv_version_history_view, name="cv_version_history"),
]