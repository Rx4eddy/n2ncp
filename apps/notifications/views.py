from django.core import signing
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import EmailOutbox, ReminderPreference


@csrf_exempt
@require_http_methods(["GET", "POST"])
def unsubscribe(request, token):
    # RFC 8058 email clients POST without browser CSRF cookies. The signed,
    # scoped capability authorizes only disabling this reminder preference.
    try:
        payload = signing.loads(token, salt="reminder-unsubscribe")
        user_id, platform = payload["user"], payload["platform"]
    except (signing.BadSignature, KeyError, TypeError):
        return HttpResponseBadRequest("Invalid unsubscribe link")
    done = request.method == "POST"
    if done:
        ReminderPreference.objects.filter(user_id=user_id, platform=platform).update(enabled=False)
        EmailOutbox.objects.filter(
            reminder__user_id=user_id, reminder__contest__platform=platform, status="pending"
        ).update(status="cancelled")
    return render(request, "unsubscribe.html", {"done": done, "platform": platform})
