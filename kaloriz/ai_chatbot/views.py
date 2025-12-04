import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services.deepseek_client import ask_ai


@csrf_exempt
def chatbot_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "")
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(message, str) or not message.strip():
        return JsonResponse({"error": "Message is required"}, status=400)

    try:
        reply = ask_ai(message)
        return JsonResponse({"reply": reply})
    except Exception as exc:  # safeguard to avoid exposing stack traces
        return JsonResponse({"error": str(exc)}, status=500)
