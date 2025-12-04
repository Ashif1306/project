import json
from json import JSONDecodeError

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services.deepseek_client import ask_ai


@csrf_exempt
def chatbot_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    raw_body = request.body
    print(f"Raw request body: {raw_body!r}")

    message = ""

    if request.content_type == "application/json":
        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            message = data.get("message", "")
        except (JSONDecodeError, ValueError, TypeError) as exc:
            return JsonResponse(
                {"error": f"Invalid JSON payload: {exc}"}, status=400
            )
    else:
        message = request.POST.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return JsonResponse(
            {"error": "Field 'message' tidak ditemukan atau kosong."}, status=400
        )

    try:
        reply = ask_ai(message)
        return JsonResponse({"reply": reply})
    except Exception as exc:  # safeguard to avoid exposing stack traces
        return JsonResponse({"error": str(exc)}, status=500)
