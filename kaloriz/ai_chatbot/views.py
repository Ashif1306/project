from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils import timezone

from ai_chatbot.services.openrouter_client import ask_ai
from ai_chatbot.utils.intent_classifier import classify_intent
from core.models import Order


@login_required
def chatbot_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    message = (request.POST.get("message") or "").strip()
    if not message:
        return JsonResponse({"reply": "Tuliskan pesanmu agar aku bisa membantu, ya!"})

    intent = classify_intent(message)

    if intent == "TRACK_ORDER":
        orders = Order.objects.filter(user=request.user).order_by("-created_at")[:5]
        if not orders:
            reply = "Kamu belum punya pesanan di Kaloriz 😊"
        else:
            lines = ["Berikut beberapa pesanan terakhirmu:"]
            for order in orders:
                created = timezone.localtime(order.created_at)
                lines.append(
                    f"- {order.order_number} | {created.strftime('%d %b %Y')} | {order.get_status_display()}"
                )
            reply = "\n".join(lines)
        return JsonResponse({"reply": reply})

    if intent == "CANCEL_ORDER_INFO":
        reply = (
            "Pesanan yang sudah dibayar bisa dibatalkan jika statusnya belum dikemas. "
            "Silakan hubungi admin Kaloriz atau gunakan fitur pembatalan di halaman pesanan."
        )
        return JsonResponse({"reply": reply})

    faq_intents = {
        "PAYMENT_INFO": (
            "Kamu bisa bayar via transfer bank, e-wallet, atau kartu sesuai opsi yang tampil saat checkout. "
            "Pilih metode favoritmu, lalu ikuti instruksi di layar."
        ),
        "SHIPPING_INFO": (
            "Ongkir dihitung otomatis sesuai alamat dan kurir yang tersedia. Setelah pembayaran, kami siapkan pesananmu "
            "dan kirim menggunakan kurir yang dipilih."
        ),
        "OPERATIONAL_HOURS": (
            "Kami melayani pemesanan online 24/7, pengiriman mengikuti jam operasional kurir setempat."
        ),
        "CONTACT_ADMIN": (
            "Butuh bantuan cepat? Hubungi admin Kaloriz melalui halaman kontak atau tombol chat admin di akunmu."
        ),
    }

    if intent in faq_intents:
        return JsonResponse({"reply": faq_intents[intent]})

    reply = ask_ai(message)
    return JsonResponse({"reply": reply})
