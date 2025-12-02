"""Simple keyword-based intent classifier for the chatbot."""

from difflib import SequenceMatcher
from typing import Optional

INTENTS = {
    "TRACK_ORDER": ["lacak pesanan", "cek pesanan", "tracking", "order saya", "lacak order"],
    "CANCEL_ORDER_INFO": ["batalkan pesanan", "refund", "batal", "cara membatalkan"],
    "PAYMENT_INFO": ["cara bayar", "pembayaran", "metode bayar", "bayar pakai apa"],
    "SHIPPING_INFO": ["ongkir", "pengiriman", "kirim ke", "kurir"],
    "OPERATIONAL_HOURS": ["jam operasional", "jam buka", "jam kerja", "buka sampai jam berapa"],
    "CONTACT_ADMIN": ["hubungi admin", "kontak admin", "whatsapp admin", "chat admin"],
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def classify_intent(text: str) -> Optional[str]:
    """Return the best matching intent or None if confidence is low."""

    cleaned = (text or "").strip().lower()
    if not cleaned:
        return None

    best_intent = None
    best_score = 0.0

    for intent, keywords in INTENTS.items():
        for keyword in keywords:
            if keyword in cleaned:
                score = 1.0
            else:
                score = _similarity(cleaned, keyword)

            if score > best_score:
                best_intent = intent
                best_score = score

    return best_intent if best_score >= 0.45 else None
