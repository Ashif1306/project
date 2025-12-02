from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "created_at", "updated_at", "ip_address")
    search_fields = ("session_key", "ip_address", "user_agent")
    ordering = ("-created_at",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "sender", "intent", "created_at")
    list_filter = ("sender", "intent", "created_at")
    search_fields = ("message", "session__session_key")
    ordering = ("-created_at",)
