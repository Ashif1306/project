# AI Chatbot (Kaloriz)

Tambahan konfigurasi agar Asisten Kaloriz terhubung ke OpenRouter dan siap dipakai.

## Konfigurasi .env
Buat atau lengkapi file `.env` di root proyek (selevel `manage.py`) dengan nilai berikut:

```
OPENROUTER_API_KEY=<contoh_placeholder_key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
GEMINI_MODEL_ID=google/gemini-2.0-flash-exp:free
```

## Pengaturan di `settings.py`
Pastikan `python-dotenv` sudah terpasang (sudah ada di `requirements.txt`). Di `kaloriz/settings.py` sudah dilakukan `load_dotenv()` untuk membaca `.env`. Tambahkan variabel berikut agar bisa diakses di seluruh proyek:

```python
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "google/gemini-2.0-flash-exp:free")
```

## Cara Mengakses dari Modul Lain
Gunakan `django.conf.settings` untuk membaca nilai konfigurasi di mana pun dibutuhkan:

```python
from django.conf import settings

api_key = settings.OPENROUTER_API_KEY
base_url = settings.OPENROUTER_BASE_URL
model_id = settings.GEMINI_MODEL_ID
```

Nilai tersebut kemudian dipakai oleh client OpenRouter di `ai_chatbot/services/openrouter_client.py`.
