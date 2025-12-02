import json
import re
from collections import Counter
from datetime import timedelta
from typing import Optional

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Order

from .models import ChatMessage, ChatSession

# ===============================
# Intent Detection
# ===============================


INTENT_KEYWORDS = {
    "lacak_pesanan": [
        "lacak",
        "lacak pesanan",
        "cek pesanan",
        "status pesanan",
        "order saya",
    ],
    "promo": ["promo", "diskon", "voucher", "kode promo", "spesial minggu ini"],
    "cara_pembayaran": [
        "bayar",
        "pembayaran",
        "transfer",
        "qris",
        "metode bayar",
        "cara bayar",
    ],
    "pengiriman": [
        "ongkir",
        "pengiriman",
        "kirim",
        "kurir",
        "biaya kirim",
        "kirim ke",
    ],
    "rekomendasi_produk": ["rekomendasi", "makanan sehat", "diet", "tinggi protein"],
    "cara_pemesanan": [
        "pesan",
        "order",
        "beli",
        "checkout",
        "cara pesan",
        "cara pemesanan",
    ],
    "info_produk": [
        "produk",
        "menu",
        "kategori",
        "makanan sehat",
        "minuman",
        "camilan",
    ],
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
        "Berikut cara pembayaran di Kaloriz:\n"
        "1) Transfer bank: pilih bank [nama bank] → transfer sesuai total → upload bukti.\n"
        "2) E-wallet: pilih e-wallet [nama e-wallet] → ikuti instruksi aplikasi → pastikan saldo cukup.\n"
        "3) QRIS: pilih QRIS → scan kode di layar → konfirmasi setelah berhasil."
    ),
    "pengiriman": (
        "Pengiriman Kaloriz menggunakan kurir reguler/instan yang dapat Anda pilih. "
        "Estimasi tiba 1-3 hari kerja untuk area utama; luar kota bisa lebih lama. "
        "Cek ongkir saat checkout, tersedia opsi free ongkir di nominal tertentu "
        "(silakan sesuaikan sesuai kebijakan)."
    ),
    "info_produk": (
        "Kaloriz punya pilihan: makanan sehat, minuman segar, dan camilan rendah kalori. "
        "Buka menu Produk untuk lihat detail lengkap tiap kategori."
    ),
    "promo": (
        "Saat ini Kaloriz punya promo spesial minggu ini: [ISI PROMO DI SINI]. Untuk "
        "detail promo terbaru, cek banner di halaman utama atau menu Promo."
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
    """Return detected intent based on simple keyword matching and regex."""

    if not message:
        return "greeting"

    lowered = message.lower()

    # Deteksi kode pesanan seperti KLRZ123 atau #KLRZ123
    if re.search(r"(?:#?klrz)(\d+)", lowered, flags=re.IGNORECASE):
        return "cek_pesanan"

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return intent
    return "fallback"


def _build_order_reply(message: str) -> str:
    """Cari kode pesanan di pesan lalu kembalikan status atau info tidak ditemukan."""

    match = re.search(r"(?:#?KLRZ)(\d+)", message, flags=re.IGNORECASE)
    if not match:
        return "Kode pesanan tidak ditemukan, pastikan penulisannya benar ya 😊 (contoh: KLRZ123)."

    order_code = f"KLRZ{match.group(1)}".upper()
    order = Order.objects.filter(order_number__iexact=order_code).first()

    if not order:
        return "Kode pesanan tidak ditemukan, pastikan penulisannya benar ya 😊 (contoh: KLRZ123)."

    status_text = _format_order_status(getattr(order, "status", ""), order)
    return f"Status pesanan {order.order_number}: {status_text}."


def _build_recommendation_reply(message: str) -> str:
    """Beri rekomendasi produk berdasarkan kata kunci sederhana."""

    from catalog.models import Product

    lowered = message.lower()
    queryset = Product.objects.filter(available=True)

    if "tinggi protein" in lowered:
        queryset = queryset.filter(protein__isnull=False).order_by("-protein")
    elif "diet" in lowered:
        queryset = queryset.filter(calories__isnull=False).order_by("calories")
    else:
        queryset = queryset.order_by("-is_featured", "-created_at")

    products = list(queryset[:3])

    if not products:
        return (
            "Saat ini belum ada rekomendasi yang cocok untuk kata kunci tersebut. "
            "Coba lihat langsung di menu Produk ya 😊."
        )

    lines = ["Berikut beberapa rekomendasi produk untukmu:"]
    for idx, product in enumerate(products, start=1):
        price = product.discount_price or product.price
        lines.append(
            f"{idx}. {product.name} - Rp{price:,.0f} - {product.get_absolute_url()}"
        )

    return "\n".join(lines)


def _format_order_status(status: str, order: Optional[Order] = None) -> str:
    """Map status internal Order ke teks manusia. Sesuaikan dengan model Order di project."""

    status_mapping = {
        "pending": "Menunggu pembayaran",
        "paid": "Pembayaran berhasil, menunggu diproses",
        "processing": "Sedang diproses",
        "shipped": "Sedang dikirim",
        "delivered": "Pesanan selesai",
        "cancelled": "Pesanan dibatalkan",
    }
    status_text = status_mapping.get(status)
    if not status_text and order and hasattr(order, "get_status_display"):
        status_text = order.get_status_display()
    return status_text or status


def _order_to_summary(order: Order) -> dict:
    """Kembalikan data ringkas pesanan untuk daftar. Sesuaikan field kode/tanggal jika perlu."""

    created_at = timezone.localtime(order.created_at)
    return {
        # Sesuaikan `order_number` dengan field kode pesanan di model Order jika berbeda.
        "code": getattr(order, "order_number", getattr(order, "code", "")).upper(),
        "date": created_at.strftime("%d %b %Y"),
        "status": _format_order_status(getattr(order, "status", ""), order),
    }


def _build_order_detail_reply(order: Order) -> str:
    """Bangun teks detail pesanan untuk balasan chatbot."""

    created_at = timezone.localtime(order.created_at)
    status_text = _format_order_status(getattr(order, "status", ""), order)

    # Ambil total. Sesuaikan nama field total_amount/total sesuai model Order di project.
    total_amount = getattr(order, "total_amount", None)
    if total_amount is None:
        total_amount = getattr(order, "total", 0)

    items = getattr(order, "items", None)
    item_list = []
    if items:
        for item in items.all():
            name = getattr(item, "product_name", getattr(item.product, "name", "Item"))
            qty = getattr(item, "quantity", 0)
            item_list.append(f"{qty}x {name}")
    item_summary = ", ".join(item_list) if item_list else "(Detail item tidak tersedia)"

    # Ambil alamat pengiriman. Sesuaikan jika field menggunakan TextField langsung.
    address_text = ""
    if getattr(order, "shipping_address", None):
        address_text = str(order.shipping_address)
    elif getattr(order, "address", None):
        address_text = order.address

    tracking_number = getattr(order, "tracking_number", "")

    lines = [
        f"Detail pesanan {getattr(order, 'order_number', getattr(order, 'code', '')).upper()}:",
        f"Tanggal: {created_at.strftime('%d %b %Y')}",
        f"Status: {status_text}",
        f"Item: {item_summary}",
        f"Total: Rp{total_amount:,.0f}",
    ]

    if address_text:
        lines.append(f"Alamat: {address_text}")
    if tracking_number:
        lines.append(f"No. Resi: {tracking_number}")

    return "\n".join(lines)


def get_bot_reply(intent: str, message: str) -> str:
    """Bangun balasan berdasarkan intent, termasuk logika dinamis."""

    if intent == "cek_pesanan":
        return _build_order_reply(message)
    if intent == "rekomendasi_produk":
        return _build_recommendation_reply(message)

    return REPLIES.get(intent, REPLIES["fallback"])


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

        action = data.get("action")
        order_code = (data.get("order_code") or "").strip().upper()
        user_message = (data.get("message") or "").strip()

        # Permintaan detail pesanan dari quick reply/button
        if action == "track_order" and order_code:
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.USER,
                message=order_code,
                intent="lacak_pesanan",
            )

            if not request.user.is_authenticated:
                reply_text = (
                    "Untuk melacak pesanan, silakan login terlebih dahulu ke akun Kaloriz ya 😊"
                )
                ChatMessage.objects.create(
                    session=session,
                    sender=ChatMessage.BOT,
                    message=reply_text,
                    intent="lacak_pesanan_detail",
                )
                return JsonResponse({"reply": reply_text, "intent": "lacak_pesanan_detail"})

            # Sesuaikan pencarian `order_number`/`code` dengan field kode pesanan di model Order.
            order = (
                Order.objects.filter(user=request.user, order_number__iexact=order_code)
                .order_by("-created_at")
                .first()
            )
            if not order:
                reply_text = (
                    "Pesanan dengan kode tersebut tidak ditemukan. Pastikan kamu memilih kode yang benar ya 😊"
                )
            else:
                reply_text = _build_order_detail_reply(order)

            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent="lacak_pesanan_detail",
            )
            return JsonResponse({"reply": reply_text, "intent": "lacak_pesanan_detail"})

        intent = detect_intent(user_message)
        if user_message:
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.USER,
                message=user_message,
                intent=intent,
            )
    else:  # GET request returns greeting to initialize widget
        user_message = ""
        intent = "greeting"

    # Intent baru: lacak pesanan tanpa kode spesifik
    if intent == "lacak_pesanan":
        if not request.user.is_authenticated:
            reply_text = (
                "Untuk melacak pesanan, silakan login terlebih dahulu ke akun Kaloriz ya 😊"
            )
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent=intent,
            )
            return JsonResponse({"reply": reply_text, "intent": intent})

        orders = list(Order.objects.filter(user=request.user).order_by("-created_at")[:5])
        if not orders:
            reply_text = (
                "Kamu belum punya pesanan di Kaloriz. Silakan lakukan pemesanan dulu ya 😊"
            )
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent=intent,
            )
            return JsonResponse({"reply": reply_text, "intent": intent})

        order_data = [_order_to_summary(order) for order in orders]
        reply_text = "Berikut 5 pesanan terakhirmu. Pilih salah satu untuk melihat detailnya:"
        ChatMessage.objects.create(
            session=session,
            sender=ChatMessage.BOT,
            message=reply_text,
            intent=intent,
        )
        return JsonResponse({"reply": reply_text, "intent": intent, "orders": order_data})

    reply_text = get_bot_reply(intent, user_message)
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
