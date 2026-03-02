from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.orientation_dashboard, name='orientation_dashboard'),
    path('history/', views.orientation_history_view, name='orientation_history'),

    path('tracks/', views.track_list_view, name='track_list'),
    path('tracks/search/', views.track_search_view, name='track_search'),
    path('tracks/<slug:slug>/', views.track_detail_view, name='track_detail'),

    path('schools/<int:pk>/', views.school_detail_view, name='school_detail'),
    path('jobs/', views.job_list_view, name='job_list'),
    path('jobs-recommendes/', views.orientation_job_recommendations, name='job_recommende'),

    # Détail d'un métier (via sa clé primaire ID)
    path('job/<int:pk>/', views.job_detail_view, name='job_detail'),

    



    # ... tes autres URLs ...

    path('schools/search/', views.school_search_view, name='school_search'),


    path('test/', views.orientation_test_view, name='orientation_test'),
    path('tests/', views.orientation_test_page, name='orientation_test_page'),
    path('results/<int:result_id>/', views.orientation_result_detail_view, name='orientation_result_detail'),
    
    # AI Orientation Test
    path('ai-test/', views.ai_orientation_test_view, name='ai_orientation_test'),
    path('ai-api/', views.ai_orientation_api, name='ai_orientation_api'),
]