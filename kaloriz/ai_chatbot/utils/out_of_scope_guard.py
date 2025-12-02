BLOCKED_KEYWORDS = [
    "pancasila",
    "sila",
    "agama",
    "polit",
    "presiden",
    "pilpres",
    "ujian",
    "soal",
    "makalah",
    "skripsi",
    "esai",
    "essay",
    "bom",
    "hacker",
    "peretasan",
    "ai lain",
]

OUT_OF_SCOPE_RESPONSE = (
    "Maaf, aku hanya bisa membantu pertanyaan seputar Kaloriz ya 😊 Misalnya pemesanan, "
    "pembayaran, produk, ongkir, promo, atau bantuan pelanggan."
)


def is_out_of_scope(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLOCKED_KEYWORDS)
