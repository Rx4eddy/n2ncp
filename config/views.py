from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.contests.models import Contest
from apps.journal.services import analytics
from apps.recommendations.services import recommend


@login_required
def dashboard(request):
    return render(
        request,
        "dashboard.html",
        {
            "stats": analytics(request.user),
            "recommendations": recommend(request.user, limit=3),
            "contests": Contest.objects.filter(start_at__gt=timezone.now(), cancelled=False)[:3],
        },
    )


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        from django.core.cache import cache

        cache.set("health-probe", "ok", 30)
        if cache.get("health-probe") != "ok":
            raise RuntimeError("Cache unavailable")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
