"""Simple intent classifier using fuzzy matching against predefined intents."""

from difflib import SequenceMatcher

INTENTS = {
    "TRACK_ORDER": [
        "lacak pesanan",
        "cek pesanan",
        "status pesanan",
        "tracking",
        "order saya sampai mana",
    ],
    "PAYMENT_INFO": [
        "cara pembayaran",
        "metode pembayaran",
        "bayar gimana",
        "pembayaran",
        "transfer kemana",
    ],
    "SHIPPING_INFO": [
        "ongkir",
        "biaya kirim",
        "pengiriman",
        "kirim ke",
        "estimasi sampai",
    ],
    "OPERATIONAL_HOURS": [
        "jam operasional",
        "jam buka",
        "buka jam berapa",
        "hari apa saja buka",
    ],
    "CONTACT_ADMIN": [
        "hubungi admin",
        "kontak admin",
        "nomor admin",
        "cs kaloriz",
        "customer service",
    ],
}


THRESHOLD = 0.6


def classify_intent(text: str):
    """Return the best intent match for the given text or None if below threshold."""

    normalized = (text or "").lower()
    best_intent = None
    best_score = 0.0

    for intent, phrases in INTENTS.items():
        for phrase in phrases:
            score = SequenceMatcher(None, normalized, phrase).ratio()
            if score > best_score:
                best_score = score
                best_intent = intent

    if best_score < THRESHOLD:
        return None

    return best_intent
