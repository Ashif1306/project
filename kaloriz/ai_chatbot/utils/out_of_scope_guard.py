BLOCKED_KEYWORDS = [
    "bom",
    "senjata",
    "hacker",
    "hack",
    "peretasan",
    "rakit",
    "narkoba",
    "teror",
]

OUT_OF_SCOPE_RESPONSE = (
    "Maaf, aku nggak bisa membantu permintaan itu. Kalau mau, aku bisa bantu hal lain seputar "
    "Kaloriz atau pertanyaan umum yang aman 😊"
)


def is_out_of_scope(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLOCKED_KEYWORDS)
