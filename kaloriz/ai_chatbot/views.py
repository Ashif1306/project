from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse

from ai_chatbot.services.openrouter_client import ask_ai
from ai_chatbot.utils.out_of_scope_guard import OUT_OF_SCOPE_RESPONSE, is_out_of_scope


@login_required
def chatbot_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    message = (request.POST.get("message") or "").strip()
    if not message:
        return JsonResponse({"reply": "Tuliskan pesanmu agar aku bisa membantu, ya!"})

    if is_out_of_scope(message):
        return JsonResponse({"reply": OUT_OF_SCOPE_RESPONSE})

    reply = ask_ai(message)
    return JsonResponse({"reply": reply})
