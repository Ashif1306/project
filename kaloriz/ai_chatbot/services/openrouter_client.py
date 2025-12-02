"""OpenRouter chat client with automatic model fallbacks."""

import logging
from typing import Any

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Kamu adalah Asisten Kaloriz, chatbot resmi e-commerce Kaloriz. "
    "Gunakan Bahasa Indonesia yang ramah, sopan, ringkas, dan fokus pada topik Kaloriz saja: "
    "pemesanan, pembayaran, ongkir, produk, promo, jam operasional dan bantuan pelanggan. "
    "Jangan menjawab hal yang di luar konteks."
)

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
        "temperature": 0.5,
    }


def _is_rate_limited_error(data: dict[str, Any]) -> bool:
    error_block = data.get("error") or {}
    provider = (error_block.get("metadata") or {}).get("provider", "")
    message = str(error_block.get("message", ""))
    details = str(error_block) if error_block else ""

    rate_limit_hit = "rate-limited" in message.lower() or "temporarily rate-limited" in message.lower()
    google_error = "google" in provider.lower() or "gemini" in provider.lower() or "google" in message.lower()

    return rate_limit_hit or google_error or "rate limit" in details.lower()


def _extract_content(data: dict[str, Any]) -> str | None:
    try:
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:  # pragma: no cover - defensive guard
        return None


def ask_ai(message: str) -> str:
    """Call OpenRouter with fallback models and return the AI response text."""

    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    referer = getattr(settings, "OPENROUTER_REFERRER", "http://localhost")

    if not api_key:
        logger.error("OPENROUTER_API_KEY is missing")
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
        except requests.RequestException as exc:  # pragma: no cover - network guard
            logger.error("OpenRouter request error for %s: %s", model, exc)
            print(f"OpenRouter request error for {model}: {exc}")
            continue

        # Fallback on HTTP status errors
        if response.status_code == 429 or response.status_code >= 500:
            logger.warning("Model %s hit status %s, falling back", model, response.status_code)
            print(f"Model {model} hit status {response.status_code}, falling back")
            continue

        try:
            data = response.json()
        except ValueError:
            logger.error("Invalid JSON response from model %s", model)
            print(f"Invalid JSON response from model {model}")
            continue

        if _is_rate_limited_error(data):
            logger.warning("Model %s returned rate-limit/provider error, falling back", model)
            print(f"Model {model} returned rate-limit/provider error, falling back")
            continue

        content = _extract_content(data)
        if content:
            return content

        logger.error("Empty content from model %s, falling back", model)
        print(f"Empty content from model {model}, falling back")

    return FINAL_FALLBACK_MESSAGE
