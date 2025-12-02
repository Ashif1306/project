"""OpenRouter client with fallback models for Kaloriz chatbot."""

from typing import Any

import requests
from django.conf import settings

SYSTEM_PROMPT = """
Kamu adalah Asisten Kaloriz, chatbot resmi e-commerce makanan sehat Kaloriz.

Peran utama kamu:
1. Menjadi customer service Kaloriz:
   - Menjelaskan cara pemesanan.
   - Menjelaskan metode pembayaran dan alur bayar.
   - Menjelaskan pengiriman & ongkir.
   - Menjelaskan jam operasional.
   - Menjelaskan produk & menu.
   - Menjelaskan promo & diskon.
   - Membantu pelanggan membaca status pesanan (kalau sudah dikirimkan oleh sistem).

2. Menjadi asisten umum yang ramah:
   - Jika user bertanya hal umum yang aman (misalnya tips belajar, gaya hidup sehat, teknologi, ide hadiah, pertanyaan pengetahuan umum, dll.), kamu boleh menjawab dengan singkat dan jelas.
   - Usahakan tetap sopan, positif, dan tidak ekstrem.

3. Batasan:
   - Jangan memberikan panduan berbahaya (misalnya kekerasan, bom, senjata, hacking ilegal).
   - Jangan ikut dalam ujaran kebencian, SARA, pornografi, atau hal yang melanggar aturan.
   - Jika user meminta hal seperti itu, tolak dengan sopan.
   - Jika pertanyaan terlalu jauh dari konteks Kaloriz dan tidak penting (misalnya diminta mengerjakan ujian/soal sekolah secara langsung), kamu boleh menjawab secara umum atau menyarankan user belajar, bukan memberikan kunci jawaban mentah.

4. Gaya bahasa:
   - Gunakan Bahasa Indonesia yang ramah, warm, dan mudah dipahami.
   - Jawaban cukup ringkas, tidak bertele-tele.
   - Boleh pakai emoji ringan seperlunya (😊, 😉, dll.), terutama untuk percakapan santai.
   - Kalau pertanyaan berkaitan langsung dengan Kaloriz, utamakan konteks Kaloriz dulu sebelum melebar.
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
