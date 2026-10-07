from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.platforms.adapters import CONTEST_PLATFORMS
from apps.platforms.models import SyncRun

from .models import Contest


@login_required
def calendar(request):
    zone = ZoneInfo(request.user.timezone)
    today = timezone.now().astimezone(zone).date()
    try:
        offset = max(-52, min(52, int(request.GET.get("week", 0))))
    except ValueError:
        offset = 0
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    start = datetime.combine(monday, time.min, zone)
    end = datetime.combine(monday + timedelta(days=7), time.min, zone)
    contests = Contest.objects.filter(start_at__gte=start, start_at__lt=end, cancelled=False)
    selected = request.GET.get("platform", "")
    if selected in CONTEST_PLATFORMS:
        contests = contests.filter(platform=selected)
    days = [{"date": monday + timedelta(days=i), "contests": []} for i in range(7)]
    for contest in contests:
        days[(contest.start_at.astimezone(zone).date() - monday).days]["contests"].append(contest)
    status = [
        SyncRun.objects.filter(platform=p, kind="contests").order_by("-started_at").first()
        for p in CONTEST_PLATFORMS
    ]
    return render(
        request,
        "calendar.html",
        {
            "days": days,
            "monday": monday,
            "previous": offset - 1,
            "next": offset + 1,
            "week": offset,
            "platforms": CONTEST_PLATFORMS,
            "selected": selected,
            "sync_status": [s for s in status if s],
        },
    )
