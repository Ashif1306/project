"""Client helper for calling OpenRouter Gemini chat completion API."""

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _build_payload(message: str) -> dict[str, Any]:
    return {
        "model": getattr(settings, "GEMINI_MODEL_ID", ""),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kamu adalah Asisten Kaloriz, chatbot resmi e-commerce Kaloriz. "
                    "Gunakan Bahasa Indonesia yang ramah, sopan, dan ringkas. Jawab hanya hal terkait Kaloriz: "
                    "cara pemesanan, pembayaran, pengiriman dan ongkir, jam operasional, produk & menu, promo & diskon, "
                    "serta bantuan pelanggan. Jika user bertanya di luar konteks Kaloriz (misalnya politik, agama, topik sensitif lain), "
                    "jawab dengan sopan bahwa kamu hanya bisa membantu seputar Kaloriz."
                ),
            },
            {"role": "user", "content": message},
        ],
        "max_tokens": 400,
        "temperature": 0.5,
    }


def ask_ai(message: str) -> str:
    """Send a prompt to Gemini via OpenRouter and return the first reply text."""

    fallback = "Maaf, sistem sedang sibuk. Coba beberapa saat lagi ya."
    base_url = getattr(settings, "OPENROUTER_BASE_URL", "").rstrip("/")
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")

    if not base_url or not api_key:
        logger.error("OpenRouter credentials are missing. Check OPENROUTER_BASE_URL and OPENROUTER_API_KEY")
        return fallback

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=_build_payload(message),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", fallback)
    except Exception as exc:  # pragma: no cover - simple defensive guard
        logger.exception("OpenRouter request failed: %s", exc)
        return fallback
