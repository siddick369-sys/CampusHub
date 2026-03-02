# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     re_path(r"ws/chat/(?P<pk>\d+)/$", consumers.ChatConsumer.as_asgi()),
# ]


from django.urls import re_path
from .consumers_call import *

websocket_urlpatterns = [
    # on utilise l'id de la conversation comme room
    re_path(r"ws/call/(?P<conversation_id>\d+)/$", CallConsumer.as_asgi()),
]