from django.urls import path
from . import views

urlpatterns = [
    path("test/", views.services_test_view, name="services_test"),
    path(
        "alerts/",
        views.service_search_alert_list_view,
        name="service_search_alert_list"
    ),
        # ... autres urls ...
    path('mes-services/', views.my_services_dashboard, name='my_services_dashboard'),
    # ... autres urls ...
    path('mes-commandes/', views.client_orders_list, name='client_orders_list'),
    
    path('mes-commandes/delete/<int:order_id>/', views.client_order_delete, name='client_order_delete'),
    path('timeslots/edit/<int:pk>/', views.provider_timeslot_edit, name='provider_timeslot_edit'),






    


    # ----------------------------------------------------
    # SERVICES OFFERS (prestations)
    # ----------------------------------------------------

    # Liste + recherche de services
    path(
        "", 
        views.service_list_view,
        name="service_list"
    ),
    
    
    path(
        "favorites/",
        views.my_favorite_services_view,
        name="my_favorite_services",
    ),
    path(
        "create/",
        views.service_create_view,
        name="service_create"
    ),
    
    path(
        "dashboard/",
        views.provider_dashboard_view,
        name="provider_dashboard"
    ),
    
    path(
        "subscription/upgrade/",
        views.subscription_upgrade_view,
        name="subscription_upgrade",
    ),
    path(
        "subscription/upgrade/<str:plan_code>/confirm/",
        views.subscription_upgrade_confirm_view,
        name="subscription_upgrade_confirm",
    ),
    
    
    path(
        "planning/",
        views.provider_timeslots_view,
        name="provider_timeslots"
    ),
    path('timeslots/delete/<int:slot_id>/', views.delete_slot, name='delete_slot'),

    path(
        "providers/<int:provider_id>/toggle-follow/",
        views.service_toggle_follow_view,
        name="service_toggle_follow",
    ),
    # stages/urls.py

    # ... ce que tu as déjà ...
    

    
    # Détail d’un service
    path(
        "<slug:slug>/",
        views.service_detail_view,
        name="service_detail"
    ),
    # services/urls.py
    # ... tes autres URLs services ...
    path(
        "provider/orders/",
        views.provider_orders_list_view,
        name="provider_orders_list",
    ),
    

    
    # ...

 # ... tes autres URLs ...
    path(
        "services/<slug:slug>/packages/create/",
        views.service_package_create_view,
        name="service_package_create",
    ),
    # ... tes autres urls ...
    path(
        "services/packages/<int:pk>/edit/",
        views.service_package_edit_view,
        name="service_package_edit"
    ),
  # ... tes autres urls ...

    path("<slug:slug>/delete/", views.service_delete_view, name="service_delete"),
    # ...
    path(
        "services/packages/<int:pk>/delete/",
        views.service_package_delete_view,
        name="service_package_delete",
    ),


    # ... le reste ...

    path(
        "orders/<int:order_id>/report/",
        views.service_order_report_view,
        name="service_order_report",
    ),
    # Création d’un service par un prestataire
    # Modification d’un service
    path(
        "<slug:slug>/edit/",
        views.service_edit_view,
        name="service_edit"
    ),
    path(
        "orders/<int:order_id>/invoice/",
        views.service_order_invoice_view,
        name="service_order_invoice",
    ),
    # ... tes autres urls services ...

    path(
        "services/favorite/<int:service_id>/toggle/",
        views.service_toggle_favorite_view,
        name="service_toggle_favorite",
    ),
    



    # ----------------------------------------------------
    # SERVICE ORDERS (commandes)
    # ----------------------------------------------------

    # Créer une commande pour un service donné
    path(
        "<slug:slug>/order/",
        views.service_order_create_view,
        name="service_order_create"
    ),
   # ...


    # ... tes autres urls ...



    # Détail d’une commande
    path(
        "orders/<int:order_id>/",
        views.service_order_detail_view,
        name="service_order_detail"
    ),
    # accounts/urls.py


    # ... tes autres urls ...


    # ... tes autres urls ...

    path(
        "orders/<int:order_id>/review/",
        views.service_review_create_view,
        name="service_review_create",
    ),

    
    path(
        "orders/<int:order_id>/accept/",
        views.service_order_accept_view,
        name="service_order_accept",
    ),
    path("orders/<int:order_id>/accept/", views.service_order_accept_view, name="service_order_accept"),
    path("orders/<int:order_id>/reject/", views.service_order_reject_view, name="service_order_reject"),
    path("orders/<int:order_id>/cancel/", views.service_order_cancel_view, name="service_order_cancel"),

    path(
        "orders/<int:order_id>/complete/provider/",
        views.service_order_mark_complete_provider_view,
        name="service_order_complete_provider",
    ),
    
    path(
        "orders/<int:order_id>/complete/client/",
        views.service_order_mark_complete_client_view,
        name="service_order_complete_client",
    ),
    


    # Prestataire change le statut de la commande
    path(
        "orders/<int:order_id>/change-status/",
        views.service_order_change_status_view,
        name="service_order_change_status"
    ),

    # Client gère la commande (annuler / compléter)
    path(
        "orders/<int:order_id>/client-action/",
        views.service_order_client_action_view,
        name="service_order_client_action"
    ),

    # ----------------------------------------------------
    # SERVICE SEARCH ALERTS (alertes de recherche)
    # ----------------------------------------------------

    # Liste de MES alertes
    # Activer / désactiver une alerte
    path(
        "alerts/<int:alert_id>/toggle/",
        views.service_search_alert_toggle_active_view,
        name="service_search_alert_toggle"
    ),

    # Supprimer une alerte
    path(
        "alerts/<int:alert_id>/delete/",
        views.service_search_alert_delete_view,
        name="service_search_alert_delete"
    ),
    


    # ----------------------------------------------------
    # PROVIDER DASHBOARD (tableau de bord prestataire)
    # ----------------------------------------------------

    ]