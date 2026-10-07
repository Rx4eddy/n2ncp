from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import signing
from django.urls import reverse


def reminder_times(user, contest):
    zone = ZoneInfo(user.timezone)
    local_date = contest.start_at.astimezone(zone).date()
    # Round-trip advances imaginary wall times across a DST gap; fold=0 chooses
    # the earlier occurrence for ambiguous wall times.
    morning = datetime.combine(local_date, time(user.morning_hour), zone).replace(fold=0)
    morning = morning.astimezone(UTC).astimezone(zone)
    times = {"before": contest.start_at - timedelta(hours=2)}
    if morning < contest.start_at:
        times["morning"] = morning.astimezone(UTC)
    return times


def unsubscribe_token(user_id, platform):
    return signing.dumps({"user": user_id, "platform": platform}, salt="reminder-unsubscribe")


def unsubscribe_url(user_id, platform):
    return settings.SITE_URL + reverse("unsubscribe", args=[unsubscribe_token(user_id, platform)])


def render_reminder(reminder):
    contest, user = reminder.contest, reminder.user
    local = contest.start_at.astimezone(ZoneInfo(user.timezone))
    url = unsubscribe_url(user.pk, contest.platform)
    subject = f"{contest.platform.title()}: {contest.title}"[:250]
    body = f"{contest.title}\nStarts: {local:%A, %d %B %Y at %H:%M %Z} ({user.timezone})\nDuration: {contest.duration_minutes} minutes\nContest: {contest.url}\n\nManage reminders: {settings.SITE_URL}/profile/\nUnsubscribe from {contest.platform} reminders: {url}\n"
    return (
        subject,
        body,
        {"List-Unsubscribe": f"<{url}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
    )
