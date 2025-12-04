"""
Klasifikasi intent sederhana berbasis keyword dan similarity.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Optional

INTENTS: Dict[str, List[str]] = {
    "TRACK_ORDER": ["lacak pesanan", "cek pesanan", "tracking", "order saya", "lacak order"],
    "CANCEL_ORDER_INFO": ["batalkan pesanan", "refund", "batal", "cara membatalkan"],
    "PAYMENT_INFO": ["cara bayar", "pembayaran", "metode bayar", "bayar pakai apa"],
    "SHIPPING_INFO": ["ongkir", "pengiriman", "kirim ke", "kurir"],
    "OPERATIONAL_HOURS": ["jam operasional", "jam buka", "jam kerja", "buka sampai jam berapa"],
    "CONTACT_ADMIN": ["hubungi admin", "kontak admin", "whatsapp admin", "chat admin"],
    "PRODUCT_INFO": [
        "produk apa saja",
        "apa saja produk",
        "jual apa saja",
        "menu apa saja",
        "varian apa saja",
        "produk yang ditawarkan",
        "kaloriz jual apa",
        "produk kaloriz",
    ],
    "GENERAL_FAQ": ["promo", "diskon", "spesial", "menu", "produk", "varian"],
}


def _similarity_score(text: str, keyword: str) -> float:
    return SequenceMatcher(None, text, keyword).ratio()


def classify_intent(text: str) -> Optional[str]:
    """
    Mengembalikan nama intent dengan skor tertinggi atau None jika tidak ada yang cocok.
    """

    normalized = (text or "").strip().lower()
    if not normalized:
        return None

    best_intent = None
    best_score = 0.0

    for intent, keywords in INTENTS.items():
        for keyword in keywords:
            if keyword in normalized:
                return intent

            score = _similarity_score(normalized, keyword)
            if score > best_score:
                best_score = score
                best_intent = intent

    return best_intent if best_score >= 0.45 else None
