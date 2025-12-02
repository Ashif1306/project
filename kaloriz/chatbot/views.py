import json
import re
from collections import Counter
from datetime import timedelta
from difflib import SequenceMatcher
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


INTENTS = [
    {
        "name": "ORDER_INFO",
        "keywords": [
            "cara pesan",
            "cara pemesanan",
            "pesan",
            "order",
            "checkout",
            "beli",
        ],
        "examples": [
            "Gimana cara pesen di Kaloriz?",
            "Aku mau order, caranya gimana?",
            "Bisa minta step checkoutnya?",
        ],
    },
    {
        "name": "PAYMENT_INFO",
        "keywords": [
            "bayar",
            "pembayaran",
            "transfer",
            "qris",
            "metode bayar",
            "cara bayar",
        ],
        "examples": [
            "Pembayarannya bisa lewat apa aja?",
            "Cara bayarnya gimana nih?",
            "Ada QRIS atau e-wallet?",
        ],
    },
    {
        "name": "SHIPPING_INFO",
        "keywords": [
            "ongkir",
            "pengiriman",
            "kirim",
            "kurir",
            "biaya kirim",
            "kirim ke",
            "antar",
        ],
        "examples": [
            "Ongkirnya berapa ya?",
            "Pengiriman pake kurir apa?",
            "Bisa kirim ke luar kota?",
        ],
    },
    {
        "name": "OPERATIONAL_HOURS",
        "keywords": [
            "jam buka",
            "jam operasional",
            "jam kerja",
            "buka jam berapa",
            "jam toko",
        ],
        "examples": [
            "Kaloriz buka jam berapa ya?",
            "Jam operasional toko kapan aja?",
            "Sampai jam berapa bisa order?",
        ],
    },
    {
        "name": "CONTACT_ADMIN",
        "keywords": [
            "kontak",
            "wa",
            "whatsapp",
            "admin",
            "cs",
            "customer service",
            "hubungi",
        ],
        "examples": [
            "Mau hubungi admin dong",
            "Ada nomor WA CS?",
            "Gimana cara chat ke admin?",
        ],
    },
]

REPLIES = {
    "greeting": (
        "Hai, aku Asisten Kaloriz! Oke, aku bantu cek ya 😄 Aku bisa bantu soal pemesanan, "
        "pembayaran, ongkir, info produk, promo, atau kontak admin. Coba klik tombol "
        "cepat di bawah atau ketik pertanyaanmu."
    ),
    "ORDER_INFO": (
        "Siap, aku bantu jelasin ya 😄 Cara pesan di Kaloriz: pilih produk → tambah ke keranjang "
        "→ klik checkout → isi alamat & penerima → pilih metode bayar → konfirmasi. Habis itu "
        "tinggal duduk manis, tim kami langsung proses ✨"
    ),
    "PAYMENT_INFO": (
        "Oke, soal pembayaran gini ya 😉:\n"
        "• Transfer bank: pilih bank yang tersedia lalu transfer sesuai total dan upload bukti.\n"
        "• E-wallet/QRIS: pilih QRIS atau e-wallet, scan/konfirmasi di aplikasinya, pastikan saldo cukup.\n"
        "• COD (jika aktif): pilih saat checkout, siapkan uang pas biar kurir senang."
    ),
    "SHIPPING_INFO": (
        "Aku cekkan info kirimannya ya 🚚✨ Pengiriman Kaloriz bisa pilih kurir reguler/instan. "
        "Estimasi tiba 1-3 hari kerja di area utama; luar kota bisa sedikit lebih lama. "
        "Ongkir keliatan di halaman checkout dan kadang ada promo gratis ongkir juga."
    ),
    "OPERATIONAL_HOURS": (
        "Kaloriz buka setiap hari jam 08.00–21.00 WIB ⏰. Di luar jam itu tetap bisa order, "
        "nanti diproses pas jam operasional ya!"
    ),
    "CONTACT_ADMIN": (
        "Butuh ngobrol langsung sama manusia? Bisa banget 😄 Chat WA admin di 08xx-xxxx-xxxx "
        "atau DM Instagram @kaloriz. Mereka standby jam 08.00–21.00 WIB."
    ),
    "info_produk": (
        "Siap, aku bantu rekomendasikan 😄 Kaloriz punya makanan sehat, minuman segar, dan "
        "camilan rendah kalori. Buka menu Produk untuk lihat detail tiap kategori, atau tulis "
        "keyword seperti 'tinggi protein' supaya aku carikan."
    ),
    "promo": (
        "Oke, aku cek promo terbaru ya 😄 Saat ini ada promo spesial minggu ini: [ISI PROMO DI SINI]. "
        "Untuk detail paling update, cek banner halaman utama atau menu Promo."
    ),
    "kontak": (
        "Siap, aku sambungkan ke tim admin ya 😄 Kamu bisa hubungi WA di 08xx-xxxx-xxxx atau "
        "Instagram @kaloriz (jam operasional 08.00-21.00 WIB)."
    ),
    "batal_pesanan": (
        "Kamu bisa membatalkan pesanan yang sudah dibayar kalau statusnya belum ‘Dikemas’. "
        "Ketik ‘lacak pesanan’ untuk pilih pesanan yang ingin dibatalkan."
    ),
    "fallback": (
        "Aku belum nangkep pertanyaannya nih 😅 Coba tanya soal cara pesan, bayar, ongkir, jam operasional, "
        "atau minta dihubungkan ke admin. Aku siap bantu!"
    ),
}


DEFAULT_QUICK_ACTIONS = ["Lacak pesanan", "Hubungi admin", "Cek metode pembayaran"]


LEGACY_KEYWORD_INTENTS = {
    "batal_pesanan": ["batal pesanan", "batalkan pesanan", "cancel order", "batalkan", "batalin"],
    "lacak_pesanan": [
        "lacak",
        "lacak pesanan",
        "cek pesanan",
        "status pesanan",
        "order saya",
    ],
    "promo": ["promo", "diskon", "voucher", "kode promo", "spesial minggu ini"],
    "rekomendasi_produk": ["rekomendasi", "makanan sehat", "diet", "tinggi protein"],
    "info_produk": [
        "produk",
        "menu",
        "kategori",
        "makanan sehat",
        "minuman",
        "camilan",
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


def classify_intent(user_text: str) -> Optional[str]:
    """Score user text against configured intents using keywords and example similarity."""

    if not user_text:
        return None

    lowered = user_text.lower()
    best_intent = None
    best_score = 0.0

    for intent in INTENTS:
        keywords = intent.get("keywords", [])
        keyword_hits = sum(1 for keyword in keywords if keyword in lowered)
        keyword_score = keyword_hits / max(len(keywords), 1)

        example_scores = [
            SequenceMatcher(None, lowered, example.lower()).ratio()
            for example in intent.get("examples", [])
        ]
        similarity_score = max(example_scores) if example_scores else 0.0

        score = (keyword_score * 0.6) + (similarity_score * 0.4)
        if score > best_score:
            best_score = score
            best_intent = intent["name"]

    if best_score < 0.5:
        return None

    return best_intent


def detect_intent(message: str) -> str:
    """Return detected intent based on simple keyword matching and regex."""

    if not message:
        return "greeting"

    lowered = message.lower()

    # Deteksi kode pesanan seperti KLRZ123 atau #KLRZ123
    if re.search(r"(?:#?klrz)(\d+)", lowered, flags=re.IGNORECASE):
        return "cek_pesanan"

    for intent, keywords in LEGACY_KEYWORD_INTENTS.items():
        if any(keyword in lowered for keyword in keywords):
            return intent

    classified_intent = classify_intent(message)
    if classified_intent:
        return classified_intent

    return "fallback"


def _build_order_reply(message: str) -> str:
    """Cari kode pesanan di pesan lalu kembalikan status atau info tidak ditemukan."""

    match = re.search(r"(?:#?KLRZ)(\d+)", message, flags=re.IGNORECASE)
    if not match:
        return (
            "Oke, aku bantu cek ya 😄 Tapi aku belum nemu kodenya. Pastikan formatnya benar ya "
            "(contoh: KLRZ123)."
        )

    order_code = f"KLRZ{match.group(1)}".upper()
    order = Order.objects.filter(order_number__iexact=order_code).first()

    if not order:
        return (
            "Oke, aku bantu cek ya 😄 Tapi aku belum nemu kodenya. Pastikan formatnya benar ya "
            "(contoh: KLRZ123)."
        )

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
            "Aku belum nemu rekomendasi yang pas untuk keyword itu. Coba buka menu Produk atau "
            "kasih keyword lain ya 😊."
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
        "Oke, aku bantu cek ya 😄 Berikut detailnya:",
        f"Pesanan: {getattr(order, 'order_number', getattr(order, 'code', '')).upper()}",
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


def _with_quick_actions(payload: dict) -> dict:
    """Tambahkan quick action default agar front-end selalu menampilkan tombol rekomendasi."""

    payload = dict(payload)
    payload.setdefault("quick_actions", DEFAULT_QUICK_ACTIONS)
    return payload


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

    chat_state = request.session.get("chat_state")

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponseBadRequest("Payload tidak valid")

        action = data.get("action")
        order_code = (data.get("order_code") or "").strip().upper()
        user_message = (data.get("message") or "").strip()

        if chat_state == "AWAITING_ORDER_CHOICE" and user_message:
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.USER,
                message=user_message,
                intent="state_selection",
            )

            reply_text = _build_order_reply(user_message)
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent="order_detail_from_state",
            )
            request.session.pop("chat_state", None)
            return JsonResponse(
                _with_quick_actions({"reply": reply_text, "intent": "order_detail_from_state"})
            )

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
                    "Oke, aku bantu cek ya 😄 Untuk melacak pesanan, silakan login dulu ke akun Kaloriz ya."
                )
                ChatMessage.objects.create(
                    session=session,
                    sender=ChatMessage.BOT,
                    message=reply_text,
                    intent="lacak_pesanan_detail",
                )
                return JsonResponse(
                    _with_quick_actions(
                        {"reply": reply_text, "intent": "lacak_pesanan_detail"}
                    )
                )

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
            return JsonResponse(
                _with_quick_actions(
                    {"reply": reply_text, "intent": "lacak_pesanan_detail"}
                )
            )

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
                "Oke, aku bantu cek ya 😄 Untuk melacak pesanan, silakan login dulu ke akun Kaloriz ya."
            )
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent=intent,
            )
            return JsonResponse(_with_quick_actions({"reply": reply_text, "intent": intent}))

        orders = list(Order.objects.filter(user=request.user).order_by("-created_at")[:5])
        if not orders:
            reply_text = (
                "Oke, aku cek ya 😄 Sepertinya kamu belum punya pesanan di Kaloriz. Coba lakukan pemesanan dulu ya."
            )
            ChatMessage.objects.create(
                session=session,
                sender=ChatMessage.BOT,
                message=reply_text,
                intent=intent,
            )
            return JsonResponse(_with_quick_actions({"reply": reply_text, "intent": intent}))

        request.session["chat_state"] = "AWAITING_ORDER_CHOICE"
        order_data = [_order_to_summary(order) for order in orders]
        reply_text = "Oke, aku bantu cek ya 😄 Berikut 5 pesanan terakhirmu. Pilih salah satu untuk lihat detailnya:"
        ChatMessage.objects.create(
            session=session,
            sender=ChatMessage.BOT,
            message=reply_text,
            intent=intent,
        )
        return JsonResponse(
            _with_quick_actions({"reply": reply_text, "intent": intent, "orders": order_data})
        )

    reply_text = get_bot_reply(intent, user_message)
    ChatMessage.objects.create(
        session=session,
        sender=ChatMessage.BOT,
        message=reply_text,
        intent=intent,
    )

    return JsonResponse(_with_quick_actions({"reply": reply_text, "intent": intent}))


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
