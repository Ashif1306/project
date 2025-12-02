import json
import os
from typing import Dict, List, Optional

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Order

from .models import ChatMessage, ChatSession

SYSTEM_PROMPT = (
    "Kamu adalah Asisten Kaloriz, chatbot resmi untuk layanan pelanggan Kaloriz "
    "(e-commerce makanan sehat). Gunakan Bahasa Indonesia yang ramah, sopan, "
    "singkat, tetapi jelas. Jawab hanya hal-hal yang berkaitan dengan Kaloriz: "
    "- cara pemesanan - pembayaran - metode bayar - pengiriman dan ongkir - jam "
    "operasional - produk dan menu - promo & diskon - bantuan pelanggan. Jangan "
    "menjawab hal di luar konteks Kaloriz. Jika user bertanya hal di luar Kaloriz, "
    "jawablah dengan sopan dan kembali ke konteks Kaloriz."
)

AI_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_AI_FALLBACK = "Maaf, aku belum paham maksudnya. Bisa jelaskan lagi?"
AI_TIMEOUT_MESSAGE = (
    "Maaf, sistem AI sedang sibuk. Coba ulangi sebentar lagi ya, atau tanyakan hal lain."
)

STATE_AWAITING_ORDER_CHOICE = "STATE_AWAITING_ORDER_CHOICE"
STATE_AWAITING_CANCEL_CONFIRM = "STATE_AWAITING_CANCEL_CONFIRM"

BASIC_RESPONSES = {
    "ORDERING": (
        "Untuk pesan di Kaloriz: pilih produk → tambah ke keranjang → checkout → isi alamat "
        "→ pilih metode bayar → konfirmasi. Tim kami lanjut proses!"
    ),
    "PAYMENT": (
        "Metode bayar yang tersedia: transfer bank, e-wallet/QRIS, dan (jika aktif) COD. "
        "Pilih saat checkout lalu ikuti petunjuk di layar."
    ),
    "SHIPPING": (
        "Ongkir terlihat di halaman checkout. Pengiriman via kurir reguler/instan, estimasi "
        "tiba 1-3 hari kerja untuk area utama."
    ),
    "OPERATING_HOURS": "Kaloriz beroperasi tiap hari pukul 08.00–21.00 WIB."
}

INTENT_KEYWORDS = {
    "TRACK_ORDER": ["lacak", "lacak pesanan", "cek pesanan", "status pesanan", "order saya"],
    "CANCEL_ORDER": ["batal pesanan", "batalkan pesanan", "cancel order", "batalin"],
    "ORDERING": ["cara pesan", "cara pemesanan", "pesan", "order", "checkout", "beli"],
    "PAYMENT": ["bayar", "pembayaran", "transfer", "qris", "metode bayar", "cara bayar"],
    "SHIPPING": ["ongkir", "pengiriman", "kirim", "kurir", "biaya kirim", "antar"],
    "OPERATING_HOURS": ["jam buka", "jam operasional", "jam kerja", "buka jam berapa", "jam toko"],
}

PACKED_OR_COMPLETED_STATUSES = {"processing", "shipped", "delivered", "cancelled"}


def ask_ai(message: str) -> str:
    """Send the message to OpenRouter Gemini 2.0 Flash model and return the reply."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return DEFAULT_AI_FALLBACK

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.Timeout:
        return AI_TIMEOUT_MESSAGE
    except Exception:
        return DEFAULT_AI_FALLBACK


def classify_intent(message: str) -> str:
    """Lightweight intent classification using keyword presence."""

    if not message:
        return "GREETING"

    lowered = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return intent

    return "OTHER"


def _format_order_status(status: str, order: Optional[Order] = None) -> str:
    mapping = {
        "pending": "Menunggu pembayaran",
        "paid": "Pembayaran diterima",
        "processing": "Sedang diproses/dikemas",
        "shipped": "Sedang dikirim",
        "delivered": "Pesanan selesai",
        "cancelled": "Pesanan dibatalkan",
    }
    if order and hasattr(order, "get_status_display"):
        return mapping.get(status) or order.get_status_display()
    return mapping.get(status, status)


def _order_to_summary(order: Order) -> Dict[str, str]:
    created_at = timezone.localtime(order.created_at)
    return {
        "id": order.id,
        "code": getattr(order, "order_number", "").upper(),
        "date": created_at.strftime("%d %b %Y"),
        "status": _format_order_status(order.status, order),
    }


def _build_order_detail_reply(order: Order) -> str:
    created_at = timezone.localtime(order.created_at)
    total_amount = getattr(order, "total", None)
    if total_amount is None:
        total_amount = getattr(order, "total_amount", 0)

    items = getattr(order, "items", None)
    item_list: List[str] = []
    if items:
        for item in items.all():
            name = getattr(item, "product_name", getattr(item.product, "name", "Item"))
            qty = getattr(item, "quantity", 0)
            item_list.append(f"{qty}x {name}")
    item_summary = ", ".join(item_list) if item_list else "(detail item tidak tersedia)"

    address_text = ""
    if getattr(order, "shipping_address", None):
        address_text = str(order.shipping_address)
    elif getattr(order, "address", None):
        address_text = str(order.address)

    lines = [
        "Oke, aku bantu cek ya 😄 Berikut detailnya:",
        f"Pesanan: {getattr(order, 'order_number', '').upper()}",
        f"Tanggal: {created_at.strftime('%d %b %Y')}",
        f"Status: {_format_order_status(order.status, order)}",
        f"Item: {item_summary}",
        f"Total: Rp{total_amount:,.0f}",
    ]

    tracking_number = getattr(order, "tracking_number", "")
    if tracking_number:
        lines.append(f"No. Resi: {tracking_number}")
    if address_text:
        lines.append(f"Alamat: {address_text}")

    return "\n".join(lines)


def _recent_orders_for_user(user, limit: int = 5) -> List[Order]:
    return list(Order.objects.filter(user=user).order_by("-created_at")[:limit])


def _json_reply(reply: str, **extra) -> JsonResponse:
    payload = {"reply": reply}
    payload.update(extra)
    return JsonResponse(payload)


def _start_tracking_flow(request, chat_session: ChatSession) -> JsonResponse:
    if not request.user.is_authenticated:
        reply_text = "Untuk melacak pesanan, silakan login dulu ke akun Kaloriz ya."
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    orders = _recent_orders_for_user(request.user)
    if not orders:
        reply_text = "Sepertinya kamu belum punya pesanan di Kaloriz. Yuk coba pesan dulu!"
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    request.session["chat_state"] = STATE_AWAITING_ORDER_CHOICE
    request.session["order_context"] = {
        "action": "track",
        "order_ids": [order.id for order in orders],
    }
    request.session.save()

    reply_text = (
        "Oke, aku bantu cek ya. Berikut 5 pesanan terakhirmu, pilih salah satu dengan mengetikkan kode pesanan:"
    )
    order_data = [_order_to_summary(order) for order in orders]
    ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
    return _json_reply(reply_text, orders=order_data)


def _start_cancel_flow(request, chat_session: ChatSession) -> JsonResponse:
    if not request.user.is_authenticated:
        reply_text = "Untuk membatalkan pesanan, silakan login dulu ke akun Kaloriz ya."
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    candidate_orders = _recent_orders_for_user(request.user)
    orders = [order for order in candidate_orders if order.status not in PACKED_OR_COMPLETED_STATUSES]
    if not orders:
        reply_text = "Aku tidak menemukan pesanan yang bisa dibatalkan saat ini."
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    request.session["chat_state"] = STATE_AWAITING_ORDER_CHOICE
    request.session["order_context"] = {
        "action": "cancel",
        "order_ids": [order.id for order in orders],
    }
    request.session.save()

    reply_text = (
        "Sebutkan kode pesanan yang ingin dibatalkan. Hanya pesanan yang belum dikemas yang bisa dibatalkan."
    )
    order_data = [_order_to_summary(order) for order in orders]
    ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
    return _json_reply(reply_text, orders=order_data)


def _handle_order_choice(request, chat_session: ChatSession, user_message: str) -> JsonResponse:
    if user_message:
        ChatMessage.objects.create(
            session=chat_session,
            sender=ChatMessage.USER,
            message=user_message,
            intent="ORDER_SELECTION",
        )

    order_context = request.session.get("order_context") or {}
    action = order_context.get("action")
    order_ids = order_context.get("order_ids", [])

    if not action or not order_ids:
        request.session.pop("chat_state", None)
        request.session.pop("order_context", None)
        return _json_reply(DEFAULT_AI_FALLBACK)

    order_code = (user_message or "").strip().upper()
    order = (
        Order.objects.filter(user=request.user, id__in=order_ids, order_number__iexact=order_code)
        .order_by("-created_at")
        .first()
    )
    if not order:
        reply_text = "Kode pesanan belum cocok. Coba ketik ulang sesuai daftar di atas ya."
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    if action == "track":
        reply_text = _build_order_detail_reply(order)
        request.session.pop("chat_state", None)
        request.session.pop("order_context", None)
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    if action == "cancel":
        if order.status in PACKED_OR_COMPLETED_STATUSES:
            reply_text = "Pesanan ini sudah dikemas atau selesai, jadi tidak bisa dibatalkan."
            request.session.pop("chat_state", None)
            request.session.pop("order_context", None)
            ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
            return _json_reply(reply_text)

        request.session["chat_state"] = STATE_AWAITING_CANCEL_CONFIRM
        request.session["order_context"] = {"action": "cancel_confirm", "selected_order": order.id}
        request.session.save()
        reply_text = (
            f"Kamu yakin mau membatalkan pesanan {order.order_number}? Jawab 'ya' untuk lanjut atau 'tidak' untuk batal."
        )
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    request.session.pop("chat_state", None)
    request.session.pop("order_context", None)
    return _json_reply(DEFAULT_AI_FALLBACK)


def _handle_cancel_confirmation(request, chat_session: ChatSession, user_message: str) -> JsonResponse:
    decision = (user_message or "").strip().lower()
    if user_message:
        ChatMessage.objects.create(
            session=chat_session,
            sender=ChatMessage.USER,
            message=user_message,
            intent="CANCEL_CONFIRMATION",
        )
    order_id = (request.session.get("order_context") or {}).get("selected_order")
    order = Order.objects.filter(user=request.user, id=order_id).first()

    if decision not in {"ya", "y", "yes", "iya", "ok"}:
        reply_text = "Baik, pembatalan dibatalkan. Ada yang lain bisa aku bantu?"
        request.session.pop("chat_state", None)
        request.session.pop("order_context", None)
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    if not order:
        reply_text = "Pesanan tidak ditemukan. Coba ulangi proses pembatalan ya."
        request.session.pop("chat_state", None)
        request.session.pop("order_context", None)
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    if order.status in PACKED_OR_COMPLETED_STATUSES:
        reply_text = "Pesanan sudah dikemas atau selesai sehingga tidak bisa dibatalkan."
        request.session.pop("chat_state", None)
        request.session.pop("order_context", None)
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    order.status = "cancelled"
    order.save(update_fields=["status"])

    reply_text = f"Pesanan {order.order_number} berhasil dibatalkan. Ada yang lain bisa aku bantu?"
    request.session.pop("chat_state", None)
    request.session.pop("order_context", None)
    ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
    return _json_reply(reply_text)


@csrf_exempt
def chatbot_reply(request):
    if not request.session.session_key:
        request.session.save()

    chat_session, _ = ChatSession.objects.get_or_create(
        session_key=request.session.session_key,
        defaults={
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            "ip_address": request.META.get("REMOTE_ADDR", ""),
        },
    )

    chat_state = request.session.get("chat_state")

    if request.method != "POST":
        reply_text = (
            "Hai, aku Asisten Kaloriz! Aku bisa bantu soal pesanan, pembayaran, ongkir, atau info toko."
        )
        return _json_reply(reply_text)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest("Payload tidak valid")

    user_message = (data.get("message") or "").strip()

    if chat_state == STATE_AWAITING_ORDER_CHOICE:
        return _handle_order_choice(request, chat_session, user_message)

    if chat_state == STATE_AWAITING_CANCEL_CONFIRM:
        return _handle_cancel_confirmation(request, chat_session, user_message)

    intent = classify_intent(user_message)

    if user_message:
        ChatMessage.objects.create(
            session=chat_session,
            sender=ChatMessage.USER,
            message=user_message,
            intent=intent,
        )

    if intent == "TRACK_ORDER":
        return _start_tracking_flow(request, chat_session)

    if intent == "CANCEL_ORDER":
        return _start_cancel_flow(request, chat_session)

    if intent in BASIC_RESPONSES:
        reply_text = BASIC_RESPONSES[intent]
        ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=reply_text)
        return _json_reply(reply_text)

    ai_reply = ask_ai(user_message)
    if not ai_reply:
        ai_reply = DEFAULT_AI_FALLBACK

    ChatMessage.objects.create(session=chat_session, sender=ChatMessage.BOT, message=ai_reply)
    return _json_reply(ai_reply)


@login_required
def chatbot_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Hanya staff yang dapat mengakses dashboard chatbot.")

    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()

    intents = ChatMessage.objects.filter(sender=ChatMessage.BOT).values_list("intent", flat=True)
    intent_counts = {}
    for intent in intents:
        if not intent:
            continue
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    context = {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "intent_counts": intent_counts,
    }

    return render(request, "chatbot/dashboard.html", context)
