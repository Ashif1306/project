import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.text import Truncator
from django.views.decorators.csrf import csrf_exempt

from catalog.models import Product
from core.models import Order

from .models import ChatMessage, ChatSession

# ===============================
# Intent Detection
# ===============================


INTENT_KEYWORDS = {
    "panduan_produk": [
        "produk",
        "menu",
        "kategori",
        "rekomendasi",
        "makanan sehat",
        "minuman",
        "camilan",
        "paket",
        "diet",
    ],
    "lacak_pesanan": [
        "lacak pesanan",
        "tracking",
        "cek order",
        "status pesanan",
        "resi",
    ],
    "promo": [
        "promo",
        "diskon",
        "voucher",
        "kode promo",
        "sale",
        "potongan",
        "spesial minggu ini",
    ],
    "pembayaran": [
        "bayar",
        "pembayaran",
        "transfer",
        "qris",
        "metode bayar",
        "cara bayar",
        "virtual account",
        "e-wallet",
        "pesan",
        "order",
        "beli",
        "checkout",
        "cara pesan",
        "cara pemesanan",
    ],
    "pengiriman": [
        "ongkir",
        "pengiriman",
        "kirim",
        "kurir",
        "biaya kirim",
        "kirim ke",
    ],
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


def _format_currency(value) -> str:
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    return f"Rp {number_format(amount, decimal_pos=0, force_grouping=True)}"


def _append_closing(text: str) -> str:
    closing = "Ada yang bisa saya bantu lagi?"
    if text.strip().endswith(closing):
        return text
    return f"{text}\n\n{closing}"


def _detect_order_in_message(user, message: str):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    lowered = (message or "").lower()
    if not lowered:
        return None

    for order_number in Order.objects.filter(user=user).values_list(
        "order_number", flat=True
    ):
        if order_number.lower() in lowered:
            try:
                return Order.objects.select_related("shipping_address").get(
                    user=user, order_number=order_number
                )
            except Order.DoesNotExist:  # pragma: no cover - safety
                continue
    return None


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


def _summarize_products(products):
    items = []
    for product in products:
        price_label = _format_currency(product.get_display_price())
        summary = f"- {product.name} ({product.category.name}) – {price_label}"
        description = Truncator(product.description).chars(100)
        if description:
            summary += f" — {description}"
        if not product.available or product.stock <= 0:
            summary += " (Produk ini sedang out of stock.)"
        items.append(summary)
    return "\n".join(items)


def _product_reply() -> str:
    products = (
        Product.objects.select_related("category")
        .filter(available=True)
        .order_by("-created_at")[:5]
    )
    if not products:
        return _append_closing("Maaf, datanya belum tersedia.")

    intro = (
        "Berikut beberapa pilihan produk Kaloriz untukmu (nama, harga, kategori, dan deskripsi singkat):"
    )
    product_lines = _summarize_products(products)
    outro = (
        "Butuh rekomendasi lebih spesifik? Kasih tahu kebutuhanmu, misalnya camilan sehat, minuman rendah kalori, atau paket hemat."
    )
    return _append_closing(f"{intro}\n{product_lines}\n{outro}")


def _promo_reply() -> str:
    promo_products = []
    for product in Product.objects.select_related("category").filter(available=True):
        if product.is_on_sale():
            discount = product.get_discount_percentage()
            price_label = _format_currency(product.get_display_price())
            base_price = _format_currency(product.price)
            promo_products.append(
                f"- {product.name} ({product.category.name}) – {price_label} dari {base_price} (diskon {discount}%)"
            )

    if not promo_products:
        return _append_closing(
            "Saat ini belum ada promo aktif, tapi pantau terus halaman promo ya!"
        )

    intro = "Ini promo yang lagi aktif:" if len(promo_products) == 1 else "Ini beberapa promo yang lagi aktif:"
    return _append_closing(f"{intro}\n" + "\n".join(promo_products))


def _payment_reply() -> str:
    methods = (
        "Metode pembayaran yang tersedia: Transfer Bank, Virtual Account, QRIS, dan E-wallet (Dana, OVO, Gopay)."
    )
    steps = (
        "Langkah checkout:\n"
        "1) Masukkan produk ke keranjang\n"
        "2) Pilih metode pembayaran\n"
        "3) Selesaikan pembayaran\n"
        "4) Upload bukti jika manual\n"
        "5) Pesanan akan divalidasi otomatis"
    )
    return _append_closing(f"{methods}\n{steps}")


def _shipping_reply(city_hint: str | None = None) -> str:
    city_note = "" if not city_hint else f" untuk wilayah {city_hint}"
    courier_info = (
        "Ekspedisi yang tersedia: JNE, J&T, dan Sicepat. Estimasi kirim rata-rata 2–4 hari kerja"
        f"{city_note}. Ongkir dihitung otomatis saat checkout sesuai alamat tujuan."
    )
    return _append_closing(courier_info)


def _tracking_overview(user) -> str:
    if not getattr(user, "is_authenticated", False):
        return _append_closing(
            "Untuk cek status pesanan, silakan login dulu ya supaya aku bisa tampilkan riwayat pesananmu."
        )

    orders = list(Order.objects.filter(user=user).order_by("-created_at")[:5])
    if not orders:
        return _append_closing(
            "Maaf, datanya belum tersedia karena belum ada pesanan. Yuk mulai belanja dulu!"
        )

    lines = ["Ini 5 pesanan terakhirmu:"]
    for order in orders:
        status_label = order.get_status_display()
        date_label = order.created_at.strftime("%d %b %Y")
        line = f"- {order.order_number} – {status_label} (pesan {date_label})"
        if order.tracking_number:
            line += f" | Resi: {order.tracking_number}"
        lines.append(line)

    lines.append(
        "Sebutkan nomor pesanan yang mau dicek, nanti aku tampilkan detail lengkapnya."
    )
    return _append_closing("\n".join(lines))


def _order_detail_reply(order: Order) -> str:
    status_label = order.get_status_display()
    created_at = order.created_at.strftime("%d %b %Y %H:%M")
    total_label = _format_currency(order.total)
    courier = order.shipping_provider or order.selected_courier or "(belum dipilih)"
    tracking = order.tracking_number or "(belum ada resi)"
    details = (
        f"Detail pesanan {order.order_number}:\n"
        f"- Status: {status_label}\n"
        f"- Tanggal pemesanan: {created_at}\n"
        f"- Total harga: {total_label}\n"
        f"- Ekspedisi: {courier}\n"
        f"- Nomor resi: {tracking}"
    )
    return _append_closing(details)


def _fallback_reply() -> str:
    return _append_closing(
        "Maaf, saya hanya bisa membantu terkait layanan dan produk Kaloriz. Coba tanyakan seputar produk, promo, pembayaran, ongkir, atau pesanan."
    )


def _greeting_reply() -> str:
    message = (
        "Halo! Saya Kaloriz, asisten belanja cerdas. Saya bisa bantu cari produk, info promo, pembayaran, ongkir & pengiriman, sampai lacak pesanan. Cukup pilih tombol cepat atau ketik pertanyaanmu."
    )
    return _append_closing(message)


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
        order_match = _detect_order_in_message(request.user, user_message)
        if order_match:
            intent = "order_detail"
            reply_text = _order_detail_reply(order_match)
        else:
            intent = detect_intent(user_message)
            if intent == "panduan_produk":
                reply_text = _product_reply()
            elif intent == "promo":
                reply_text = _promo_reply()
            elif intent == "pembayaran":
                reply_text = _payment_reply()
            elif intent == "pengiriman":
                reply_text = _shipping_reply()
            elif intent == "lacak_pesanan":
                reply_text = _tracking_overview(request.user)
            elif intent == "greeting":
                reply_text = _greeting_reply()
            else:
                reply_text = _fallback_reply()
    else:  # GET request returns greeting to initialize widget
        intent = "greeting"
        reply_text = _greeting_reply()
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
