from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ai_chatbot.services.openrouter_client import ask_ai_with_priority
from ai_chatbot.utils.intent_classifier import classify_intent
from core.models import Order


@login_required
@require_POST
def chatbot_view(request):
    """Endpoint chatbot hybrid (AI + data Order)."""

    message = (request.POST.get("message") or "").strip()
    if not message:
        return JsonResponse({"reply": "Silakan tulis pertanyaanmu dulu ya 😊"})

    intent = classify_intent(message)
    reply_text = ""

    if intent == "TRACK_ORDER":
        orders = (
            Order.objects.filter(user=request.user)
            .order_by("-created_at")[:5]
        )
        if not orders:
            reply_text = "Kamu belum punya pesanan di Kaloriz 😊"
        else:
            lines = ["Berikut beberapa pesanan terakhirmu:"]
            for order in orders:
                lines.append(
                    f"- {order.invoice_number} | {order.created_at:%d %b %Y} | {order.status}"
                )
            lines.append(
                "Jika ingin bantuan lebih lanjut, sebutkan nomor pesanan yang ingin kamu tanyakan."
            )
            reply_text = "\n".join(lines)

    elif intent == "CANCEL_ORDER_INFO":
        reply_text = (
            "Pesanan yang sudah dibayar bisa dibatalkan jika statusnya belum dikemas. "
            "Silakan hubungi admin Kaloriz atau gunakan fitur pembatalan di halaman pesanan jika tersedia."
        )

    elif intent in {"PAYMENT_INFO", "SHIPPING_INFO", "OPERATIONAL_HOURS", "CONTACT_ADMIN"}:
        context_hint = (
            "Jawab secara singkat dalam Bahasa Indonesia. "
            "Jika ada informasi harga atau kebijakan, sampaikan secara umum tanpa detail sensitif."
        )
        reply_text = ask_ai_with_priority(f"{context_hint}\n\nPertanyaan: {message}")

    else:
        reply_text = ask_ai_with_priority(message)

    return JsonResponse({"reply": reply_text})
