"""
ASGI config for CampuHub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CampuHub.settings')

# application = get_asgi_application() #et ici mettre django_asgi_app


# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             stages.routing.websocket_urlpatterns
#         )
#     ),
# })

# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import stages.routing  # on va le créer


import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from stages import routing as stages_routing
import stages.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CampuHub.settings")


django_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            stages.routing.websocket_urlpatterns
        )
    ),
})