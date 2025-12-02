from django.urls import path

from ai_chatbot.views import chatbot_view

urlpatterns = [
    path("", chatbot_view, name="chatbot"),
]
