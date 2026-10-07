import smtplib
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from apps.contests.models import Contest
from apps.notifications.models import EmailOutbox, ReminderDelivery, ReminderPreference
from apps.notifications.services import reminder_times, unsubscribe_token
from apps.notifications.tasks import deliver_email, dispatch_outbox, plan_reminders

pytestmark = pytest.mark.django_db


def contest(start):
    return Contest.objects.create(
        platform="codeforces",
        external_id="123",
        title="Round 123",
        url="https://codeforces.com/contest/123",
        start_at=start,
        duration_seconds=7200,
    )


def test_timezone_morning_and_two_hours(user):
    c = contest(datetime(2026, 10, 10, 14, tzinfo=UTC))
    result = reminder_times(user, c)
    assert result["morning"] == datetime(2026, 10, 10, 2, 30, tzinfo=UTC)
    assert result["before"] == datetime(2026, 10, 10, 12, tzinfo=UTC)


def test_morning_after_start_is_omitted(user):
    c = contest(datetime(2026, 10, 10, 0, tzinfo=UTC))
    assert "morning" not in reminder_times(user, c)


@pytest.mark.parametrize(
    "start,expected",
    [
        (datetime(2026, 3, 8, 18, tzinfo=UTC), datetime(2026, 3, 8, 12, tzinfo=UTC)),
        (datetime(2026, 11, 1, 18, tzinfo=UTC), datetime(2026, 11, 1, 13, tzinfo=UTC)),
    ],
)
def test_dst_local_morning(user, start, expected):
    user.timezone = "America/New_York"
    assert reminder_times(user, contest(start))["morning"] == expected


def test_planning_idempotent(user):
    now = datetime(2026, 10, 10, 1, tzinfo=UTC)
    contest(datetime(2026, 10, 10, 14, tzinfo=UTC))
    ReminderPreference.objects.create(user=user, platform="codeforces", enabled=True)
    with patch("apps.notifications.tasks.timezone.now", return_value=now):
        plan_reminders()
        plan_reminders()
    assert ReminderDelivery.objects.count() == 2
    assert EmailOutbox.objects.count() == 2


def ready_reminder(user):
    now = timezone.now()
    c = contest(now + timedelta(hours=2))
    ReminderPreference.objects.create(user=user, platform="codeforces", enabled=True)
    reminder = ReminderDelivery.objects.create(user=user, contest=c, kind="before", due_at=now)
    return EmailOutbox.objects.create(
        reminder=reminder, recipient=user.email, subject="reminder", body="body", available_at=now
    )


def test_delivery_idempotent(user):
    item = ready_reminder(user)
    deliver_email(item.pk)
    deliver_email(item.pk)
    assert len(mail.outbox) == 1
    item.refresh_from_db()
    assert item.status == "sent"
    assert mail.outbox[0].extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_unsubscribe_get_is_safe_post_disables(client, user):
    item = ready_reminder(user)
    token = unsubscribe_token(user.pk, "codeforces")
    url = f"/unsubscribe/{token}/"
    assert client.get(url).status_code == 200
    assert ReminderPreference.objects.get(user=user).enabled
    assert client.post(url, {"List-Unsubscribe": "One-Click"}).status_code == 200
    deliver_email(item.pk)
    item.refresh_from_db()
    assert item.status == "cancelled"
    assert len(mail.outbox) == 0


def test_invalid_unsubscribe(client):
    assert client.post("/unsubscribe/tampered/").status_code == 400


def test_rescheduled_contest_defers_existing_delivery(user):
    item = ready_reminder(user)
    c = item.reminder.contest
    c.start_at += timedelta(hours=4)
    c.save()
    deliver_email(item.pk)
    item.refresh_from_db()
    assert item.status == "pending"
    assert item.available_at > timezone.now()
    assert len(mail.outbox) == 0


def test_stale_reminder_cancelled(user):
    item = ready_reminder(user)
    c = item.reminder.contest
    c.start_at -= timedelta(hours=1)
    c.save()
    deliver_email(item.pk)
    item.refresh_from_db()
    assert item.status == "cancelled"


def test_known_rejection_retries(user):
    item = ready_reminder(user)
    with patch(
        "apps.notifications.tasks.EmailMessage.send",
        side_effect=smtplib.SMTPDataError(451, b"retry"),
    ):
        deliver_email(item.pk)
    item.refresh_from_db()
    assert item.status == "pending" and item.attempts == 1
    assert item.available_at > timezone.now()


def test_ambiguous_delivery_quarantined(user):
    item = ready_reminder(user)
    with patch("apps.notifications.tasks.EmailMessage.send", side_effect=TimeoutError):
        deliver_email(item.pk)
    item.refresh_from_db()
    assert item.status == "uncertain"


def test_worker_crash_quarantined(user):
    item = ready_reminder(user)
    item.status, item.claimed_at = "sending", timezone.now() - timedelta(minutes=10)
    item.save()
    dispatch_outbox()
    item.refresh_from_db()
    assert item.status == "uncertain"
