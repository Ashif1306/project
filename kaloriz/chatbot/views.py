import json
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import ChatMessage, ChatSession

# ===============================
# Intent Detection
# ===============================


INTENT_KEYWORDS = {
    "cara_pemesanan": [
        "pesan",
        "order",
        "beli",
        "checkout",
        "cara pesan",
        "cara pemesanan",
    ],
    "cara_pembayaran": [
        "bayar",
        "pembayaran",
        "transfer",
        "qris",
        "metode bayar",
        "cara bayar",
    ],
    "pengiriman": ["ongkir", "pengiriman", "kirim", "kurir", "biaya kirim", "kirim ke"],
    "info_produk": [
        "produk",
        "menu",
        "kategori",
        "makanan sehat",
        "minuman",
        "camilan",
    ],
    "promo": ["promo", "diskon", "voucher", "kode promo"],
    "kontak": ["kontak", "wa", "whatsapp", "admin", "cs", "jam buka", "customer service"],
    "greeting": [
        "halo",
        "hai",
        "hi",
        "assalamualaikum",
        "selamat pagi",
        "selamat siang",
        "selamat malam",
    ],
}

REPLIES = {
    "greeting": (
        "Hai! Saya Asisten Kaloriz. Saya bisa bantu soal pemesanan, pembayaran, "
        "ongkir, info produk, promo, atau kontak admin. Silakan pilih tombol cepat "
        "atau ketik pertanyaan Anda."
    ),
    "cara_pemesanan": (
        "Untuk pesan di Kaloriz: pilih produk → tambah ke keranjang → klik checkout "
        "→ isi alamat & data penerima → pilih metode bayar → konfirmasi. Pesanan Anda "
        "akan segera diproses!"
    ),
    "cara_pembayaran": (
        "Metode pembayaran yang tersedia: transfer bank, e-wallet, dan QRIS. Anda "
        "bisa menyesuaikannya di halaman checkout. (Ganti teks ini sesuai pilihan "
        "pembayaran Anda.)"
    ),
    "pengiriman": (
        "Kami mengirim dari gudang Kaloriz. Estimasi pengiriman 1-3 hari kerja "
        "dengan kurir terpercaya. Cek ongkir saat checkout, promo free ongkir bisa "
        "berlaku jika tersedia."
    ),
    "info_produk": (
        "Kaloriz punya berbagai pilihan: makanan sehat, minuman segar, dan camilan "
        "rendah kalori. Jelajahi katalog di menu Produk untuk detail lengkap."
    ),
    "promo": (
        "Info promo terbaru ada di halaman utama atau banner. Anda bisa gunakan kode "
        "voucher yang sedang aktif di checkout. (Ubah teks ini sesuai promo Anda.)"
    ),
    "kontak": (
        "Butuh bantuan admin? Hubungi WhatsApp/WA di 08xx-xxxx-xxxx, Instagram "
        "@kaloriz, jam operasional 08.00-21.00 WIB. (Silakan ganti dengan kontak resmi "
        "Anda.)"
    ),
    "fallback": (
        "Maaf, Kaloriz belum paham pertanyaan itu 😅 Coba gunakan kata kunci: pemesanan, "
        "pembayaran, ongkir, produk, promo, atau kontak admin."
    ),
}


def detect_intent(message: str) -> str:
    """Return detected intent based on simple keyword matching."""

    if not message:
        return "greeting"

    lowered = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return intent
    return "fallback"


# ===============================
# Chatbot Views
# ===============================


@csrf_exempt  # Untuk produksi, sebaiknya gunakan token CSRF dan proteksi tambahan.
def chatbot_reply(request):
    """Basic endpoint to store chat history and return rule-based replies."""

    if not request.session.session_key:
        request.session.save()

    session_key = request.session.session_key
    session, _ = ChatSession.objects.get_or_create(
        session_key=session_key,
        defaults={
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            "ip_address": request.META.get("REMOTE_ADDR", ""),
        },
    )

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponseBadRequest("Payload tidak valid")

        user_message = (data.get("message") or "").strip()
        if user_message:
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.USER,
                message=user_message,
            )
        intent = detect_intent(user_message)
    else:  # GET request returns greeting to initialize widget
        intent = "greeting"

    reply_text = REPLIES.get(intent, REPLIES["fallback"])
    ChatMessage.objects.create(
        session=session,
        sender=ChatMessage.BOT,
        message=reply_text,
        intent=intent,
    )

    return JsonResponse({"reply": reply_text, "intent": intent})


@login_required
def chatbot_dashboard(request):
    """Simple analytics dashboard for chatbot usage."""

    if not request.user.is_staff:
        return HttpResponseForbidden("Hanya staff yang dapat mengakses dashboard chatbot.")

    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()

    intents = (
        ChatMessage.objects.filter(sender=ChatMessage.BOT)
        .values_list("intent", flat=True)
    )
    intent_counts = Counter(filter(None, intents))

    today = timezone.now().date()
    start_date = today - timedelta(days=6)

    sessions_last_7_days = (
        ChatSession.objects.filter(created_at__date__gte=start_date)
        .order_by("-created_at")
    )
    messages_last_7_days = ChatMessage.objects.filter(created_at__date__gte=start_date)

    context = {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "intent_counts": intent_counts,
        "sessions_last_7_days": sessions_last_7_days,
        "messages_last_7_days": messages_last_7_days,
        "start_date": start_date,
        "end_date": today,
    }

    return render(request, "chatbot/dashboard.html", context)
