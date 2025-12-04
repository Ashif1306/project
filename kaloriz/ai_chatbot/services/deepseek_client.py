"""Client for interacting with DeepSeek chat completion API with fallback logic."""

import requests
from django.conf import settings

SYSTEM_PROMPT = (
    "Kamu adalah Asisten Kaloriz, chatbot resmi e-commerce makanan sehat Kaloriz. "
    "Gunakan Bahasa Indonesia yang ramah, sopan, dan ringkas. Jawab hanya hal terkait "
    "pemesanan, pembayaran, ongkir, jam operasional, produk, promo, status pesanan, "
    "dan bantuan pelanggan. Jangan menjawab topik yang di luar konteks Kaloriz. Jika "
    "user bertanya hal tidak relevan, arahkan kembali ke konteks produk dan layanan Kaloriz."
)

MODELS = [
    "deepseek-chat",
    "deepseek-coder",
    "deepseek-reasoner-lite",
]

API_URL = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
    "Content-Type": "application/json",
}


def ask_ai(message: str) -> str:
    """Send a message to DeepSeek API with automatic fallback between models."""

    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        }

        try:
            print(f"Requesting model {model}")
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
            status_code = response.status_code
            print(f"Model {model} responded with status {status_code}")

            if status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                content = ""
                if choices:
                    message_data = choices[0].get("message", {})
                    content = (message_data.get("content") or "").strip()

                if content:
                    return content

                print(f"Model {model} returned empty content, falling back")
                continue

            if status_code == 429:
                print(f"Model {model} hit status 429, falling back")
                continue

            if status_code >= 500:
                print(f"Model {model} server error {status_code}, falling back")
                continue

            print(f"Model {model} unexpected status {status_code}, falling back")
        except Exception as exc:  # broad catch to continue fallback
            print(f"Error calling model {model}: {exc}")
            continue

    return "Maaf, server AI sedang penuh. Coba beberapa saat lagi ya 😊"
