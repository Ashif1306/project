from django.urls import path

from .views import chatbot_dashboard, chatbot_reply

app_name = "chatbot"

urlpatterns = [
    path("", chatbot_reply, name="chatbot_reply"),
    path("dashboard/", chatbot_dashboard, name="chatbot_dashboard"),
]
