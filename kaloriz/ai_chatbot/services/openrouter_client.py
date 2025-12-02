"""OpenRouter client with fallback models for Kaloriz chatbot."""

from typing import Any

import requests
from django.conf import settings

SYSTEM_PROMPT = """
Kamu adalah Asisten Kaloriz, chatbot resmi e-commerce makanan sehat Kaloriz.

ATURAN UTAMA (WAJIB DIPATUHI):
1. Kamu HANYA boleh menjawab pertanyaan yang berhubungan dengan:
   - pemesanan
   - pembayaran & metode bayar
   - pengiriman & ongkir
   - produk & menu
   - promo & diskon
   - jam operasional
   - bantuan pelanggan Kaloriz

2. Jika user bertanya di luar topik di atas:
   - JANGAN menjawab isi pertanyaan.
   - JANGAN mengarang-jawab.
   - Kembalikan jawaban templated:
     “Maaf, aku hanya bisa membantu pertanyaan seputar Kaloriz ya 😊 Misalnya pemesanan, pembayaran, produk, ongkir, promo, atau bantuan pelanggan.”

3. Gunakan Bahasa Indonesia yang sopan, ramah, dan ringkas.
"""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PRIMARY_MODEL = "google/gemini-2.0-flash-exp:free"
FALLBACK_MODELS = [
    "gpt-4o-mini:free",
    "gpt-oss-20b:free",
]
FINAL_FALLBACK_MESSAGE = "Maaf, server AI sedang penuh. Coba lagi sebentar ya 😊"


def _build_payload(model: str, message: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "max_tokens": 400,
        "temperature": 0.4,
    }


def _has_provider_error(data: dict[str, Any]) -> bool:
    error_block = data.get("error") or {}
    if not error_block:
        return False
    provider = (error_block.get("metadata") or {}).get("provider", "")
    message = str(error_block.get("message", ""))
    details = str(error_block)
    error_text = " ".join([provider, message, details]).lower()
    return "provider" in error_text or "error" in error_text or "rate" in error_text


def _extract_content(data: dict[str, Any]) -> str | None:
    try:
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        return None


def ask_ai(message: str) -> str:
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    referer = getattr(settings, "OPENROUTER_REFERRER", "http://localhost")

    if not api_key:
        return FINAL_FALLBACK_MESSAGE

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": referer,
        "X-Title": "Kaloriz Chatbot",
    }

    for model in [PRIMARY_MODEL, *FALLBACK_MODELS]:
        payload = _build_payload(model, message)
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
        except requests.RequestException:
            print(f"Model {model} mengalami kendala koneksi → fallback")
            continue

        if response.status_code == 429:
            print(f"Model {model} hit 429 → fallback")
            continue

        if response.status_code >= 500:
            print(f"Model {model} error {response.status_code} → fallback")
            continue

        try:
            data: dict[str, Any] = response.json()
        except ValueError:
            print(f"Model {model} memberi respons tidak valid → fallback")
            continue

        if _has_provider_error(data):
            print(f"Model {model} mengalami error provider → fallback")
            continue

        content = _extract_content(data)
        if content:
            return content

        print(f"Model {model} tanpa konten → fallback")

    return FINAL_FALLBACK_MESSAGE
