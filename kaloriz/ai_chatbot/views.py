from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse

from ai_chatbot.services.openrouter_client import ask_ai
from ai_chatbot.utils.intent_classifier import classify_intent
from ai_chatbot.utils.out_of_scope_guard import OUT_OF_SCOPE_RESPONSE, is_out_of_scope

INTENT_DIRECT_REPLIES = {
    "JAM_OPERASIONAL": (
        "Tim CS Kaloriz biasanya standby setiap hari pukul 08.00–21.00 WIB. "
        "Di luar jam itu, pesan akan dibalas segera setelah kami online lagi."
    ),
}

INTENT_CONTEXTS = {
    "TRACK_ORDER": (
        "Konteks Kaloriz: bantu jelaskan cara melacak status pesanan di akun Kaloriz, "
        "menu 'Pesanan Saya', kode resi jika sudah tersedia, dan estimasi pengiriman."
    ),
    "PEMBAYARAN": (
        "Konteks Kaloriz: jelaskan metode pembayaran umum (transfer bank, e-wallet populer, "
        "kartu debit/kredit jika tersedia) dan langkah checkout singkat hingga konfirmasi pembayaran."
    ),
    "PENGIRIMAN_ONGKIR": (
        "Konteks Kaloriz: uraikan opsi pengiriman, cara menghitung ongkir di checkout, dan info estimasi "
        "tiba. Tekankan bahwa ongkir dapat berbeda per lokasi dan kurir."
    ),
    "PROMO": (
        "Konteks Kaloriz: bantu pengguna memahami cara memasukkan kode promo atau voucher di halaman checkout, "
        "syarat ketentuan umum (masa berlaku, minimal belanja), dan di mana melihat promo aktif."
    ),
}


@login_required
def chatbot_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    message = (request.POST.get("message") or "").strip()
    if not message:
        return JsonResponse({"reply": "Tuliskan pesanmu agar aku bisa membantu, ya!"})

    if is_out_of_scope(message):
        return JsonResponse({"reply": OUT_OF_SCOPE_RESPONSE})

    intent = classify_intent(message)
    if intent:
        direct_reply = INTENT_DIRECT_REPLIES.get(intent)
        if direct_reply:
            return JsonResponse({"reply": direct_reply})

        context = INTENT_CONTEXTS.get(intent)
        if context:
            contextual_message = f"{message}\n\n{context}"
            reply = ask_ai(contextual_message)
            return JsonResponse({"reply": reply})

    reply = ask_ai(message)
    return JsonResponse({"reply": reply})
