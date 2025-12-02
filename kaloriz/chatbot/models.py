from django.db import models


class ChatSession(models.Model):
    """Represent a unique visitor/chat session."""

    session_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"ChatSession {self.session_key} ({self.created_at:%Y-%m-%d %H:%M})"


class ChatMessage(models.Model):
    """Store each message exchanged in the chatbot."""

    USER = "user"
    BOT = "bot"

    SENDER_CHOICES = (
        (USER, "User"),
        (BOT, "Bot"),
    )

    session = models.ForeignKey(
        ChatSession, related_name="messages", on_delete=models.CASCADE
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    intent = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple repr
        sender_label = dict(self.SENDER_CHOICES).get(self.sender, self.sender)
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {sender_label}: {self.message[:40]}"
