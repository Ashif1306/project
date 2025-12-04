from difflib import SequenceMatcher
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ai_chatbot.services.openrouter_client import ask_ai_with_priority
from ai_chatbot.utils.intent_classifier import classify_intent
from catalog.models import Product
from core.models import Order
from shipping.models import District


def format_currency(amount: Decimal) -> str:
    """Format Decimal to Indonesian Rupiah style (Rp XX.XXX)."""

    try:
        rounded = int(Decimal(amount).quantize(Decimal("1")))
    except (TypeError, ValueError):
        return "Rp 0"

    return f"Rp {rounded:,}".replace(",", ".")


def get_district_from_text(message: str):
    """Cari kecamatan yang disebutkan user berdasarkan kedekatan teks."""

    normalized = (message or "").lower()
    if not normalized:
        return None, 0.0

    districts = list(District.objects.filter(is_active=True))

    direct_matches = [d for d in districts if d.name.lower() in normalized]
    if direct_matches:
        if len(direct_matches) == 1:
            return direct_matches[0], 1.0

        best_direct = max(
            direct_matches,
            key=lambda d: SequenceMatcher(None, normalized, d.name.lower()).ratio(),
        )
        best_score = SequenceMatcher(None, normalized, best_direct.name.lower()).ratio()
        return best_direct, best_score

    best_match = None
    best_score = 0.0
    for district in districts:
        score = SequenceMatcher(None, normalized, district.name.lower()).ratio()
        if score > best_score:
            best_match = district
            best_score = score

    # Kembalikan kecamatan paling mirip jika skornya cukup tinggi
    return (best_match if best_score >= 0.6 else None), best_score


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

    # Intent produk: jawab langsung dari database, bukan dari AI
    elif intent == "PRODUCT_INFO":
        products = (
            Product.objects.filter(available=True)
            .select_related("category")
            .order_by("category__name", "name")
        )

        if not products.exists():
            reply_text = (
                "Saat ini belum ada data produk yang bisa ditampilkan di Kaloriz. "
                "Silakan cek kembali nanti ya 😊"
            )
        else:
            kategori_map = {}
            for product in products:
                kategori = getattr(product, "category", None)
                kategori_nama = getattr(kategori, "name", "Lainnya")
                kategori_map.setdefault(kategori_nama, []).append(product.name)

            lines = ["Berikut beberapa produk yang tersedia di Kaloriz:"]
            for kategori, nama_produk_list in kategori_map.items():
                contoh = ", ".join(nama_produk_list[:3])
                lines.append(f"- {kategori}: {contoh}")

            reply_text = "\n".join(lines)

    elif intent == "DISTRICT_LIST":
        districts = District.objects.filter(is_active=True).order_by("name")

        if not districts.exists():
            reply_text = (
                "Saat ini belum ada kecamatan yang terdaftar untuk pengiriman Kaloriz. "
                "Silakan cek kembali nanti ya 😊"
            )
        else:
            lines = ["Berikut daftar kecamatan yang saat ini sudah terdaftar di Kaloriz:\n"]

            for district in districts:
                lines.append(
                    (
                        f"• {district.name} → Tarif Reguler {format_currency(district.reg_cost)}, "
                        f"Express {format_currency(district.exp_cost)} "
                        f"(ETA Reguler {district.eta_reg}, ETA Express {district.eta_exp})"
                    )
                )

            lines.append(
                "\nJika kecamatanmu belum ada, silakan hubungi admin Kaloriz ya 😊"
            )

            reply_text = "\n".join(lines)

    elif intent == "ONGKIR_INFO":
        district, best_score = get_district_from_text(message)

        if district:
            reply_text = (
                f"Ongkir ke Kecamatan {district.name}:\n"
                f"• Tarif Reguler: {format_currency(district.reg_cost)} (ETA {district.eta_reg})\n"
                f"• Tarif Express: {format_currency(district.exp_cost)} (ETA {district.eta_exp})"
            )
        else:
            active_districts = District.objects.filter(is_active=True).order_by("name")

            if best_score >= 0.4:
                reply_text = (
                    "Maaf, saya belum menemukan data ongkir untuk kecamatan itu. "
                    "Silakan cek penulisan atau pilih kecamatan yang tersedia."
                )
            else:
                if not active_districts.exists():
                    reply_text = "Maaf, belum ada data ongkir yang tersedia."
                else:
                    lines = ["Berikut daftar ongkir Kaloriz:"]
                    for dist in active_districts:
                        lines.append(
                            f"- {dist.name}: {format_currency(dist.reg_cost)} (Reg) / "
                            f"{format_currency(dist.exp_cost)} (Express)"
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
