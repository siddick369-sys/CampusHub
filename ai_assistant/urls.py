from django.urls import path
from .views import ai_chat_view

app_name = "ai_assistant"

urlpatterns = [
    path("chat/", ai_chat_view, name="chat"),
]
