from datetime import timedelta
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.journal.models import JournalEntry
from apps.journal.services import analytics, canonical_problem_url
from apps.notifications.models import EmailOutbox
from apps.notifications.tasks import deliver_email
from apps.practice.models import Attempt, Module
from apps.recommendations.models import Problem

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/calendar/",
        "/journal/",
        "/profile/",
        "/practice/",
        "/recommendations/",
        "/recommendations/?platform=leetcode&topic=arrays",
        "/recommendations/?mode=review",
    ],
)
def test_required_pages_render(logged_client, seeded, path):
    response = logged_client.get(path)
    assert response.status_code == 200
    assert "Content-Security-Policy" in response


def test_all_practice_modules_render(logged_client, seeded):
    for module in Module.objects.all():
        assert logged_client.get(f"/practice/{module.slug}/").status_code == 200


@pytest.mark.parametrize(
    "path", ["/accounts/login/", "/accounts/signup/", "/accounts/password/reset/"]
)
def test_auth_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_anonymous_redirect_and_health(client):
    assert client.get("/").status_code == 302
    assert client.get("/health/").json() == {"status": "ok"}


def test_csrf_enforced(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post("/profile/", {}).status_code == 403
    assert client.post("/practice/attempt/", {}).status_code == 403


def test_registration_queues_email_and_requires_verification(client):
    response = client.post(
        "/accounts/signup/",
        {
            "email": "new@example.com",
            "password1": "this-is-a-strong-sample-password",
            "password2": "this-is-a-strong-sample-password",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="new@example.com")
    assert user.password != "this-is-a-strong-sample-password"
    assert not EmailAddress.objects.get(user=user).verified
    assert EmailOutbox.objects.count() == 1
    deliver_email(EmailOutbox.objects.get().pk)
    assert len(mail.outbox) == 1
    assert "confirm-email" in mail.outbox[0].body
    client.post(
        "/accounts/login/", {"login": user.email, "password": "this-is-a-strong-sample-password"}
    )
    assert client.get("/").status_code == 302


def test_password_reset_uses_outbox(client, user):
    response = client.post("/accounts/password/reset/", {"email": user.email})
    assert response.status_code == 302
    assert EmailOutbox.objects.filter(recipient=user.email).exists()


def test_manual_leetcode_never_fetches(logged_client, user, monkeypatch):
    import requests

    monkeypatch.setattr(
        requests, "get", lambda *a, **k: pytest.fail("Manual entry must not fetch a URL")
    )
    response = logged_client.post(
        "/journal/",
        {
            "url": "https://leetcode.com/problems/two-sum/description/",
            "title": "Two Sum",
            "solved_at": "2025-01-01T12:00",
            "notes": "<script>alert(1)</script>",
            "independent": "on",
        },
    )
    assert response.status_code == 302
    entry = JournalEntry.objects.get(user=user)
    assert entry.problem.problem_id == "two-sum"
    body = logged_client.get("/journal/").content.decode()
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_notes_isolated_between_users(logged_client, user):
    other = User.objects.create_user("other@example.com", "example-long-password")
    p = Problem.objects.create(
        platform="cses", problem_id="1", title="Example", url="https://cses.fi/problemset/task/1"
    )
    entry = JournalEntry.objects.create(user=other, problem=p, solved_at=timezone.now())
    assert logged_client.post(f"/journal/{entry.pk}/notes/", {"notes": "stolen"}).status_code == 404


def test_practice_attempt_updates_progress(logged_client, user, seeded):
    exercise = Module.objects.get(slug="cpp-stl").exercises.first()
    response = logged_client.post(
        "/practice/attempt/", {"exercise": exercise.pk, "outcome": "independent"}
    )
    assert response.status_code == 302
    assert Attempt.objects.filter(user=user, exercise=exercise).count() == 1
    assert exercise.exerciseprogress_set.get(user=user).completed_at


def test_canonical_urls():
    assert canonical_problem_url("https://codeforces.com/contest/4/problem/A")[1] == "4A"
    assert canonical_problem_url("https://leetcode.com/problems/two-sum/?foo=bar")[1] == "two-sum"
    from django.core.exceptions import ValidationError

    for url in [
        "https://localhost/private",
        "http://codeforces.com/problemset/problem/4/A",
        "https://user:password@codeforces.com/problemset/problem/4/A",
    ]:
        with pytest.raises(ValidationError):
            canonical_problem_url(url)


def test_streak_uses_local_days(user):
    now = timezone.now()
    from zoneinfo import ZoneInfo

    # Anchor away from midnight so the three dates are consecutive locally.
    now = now.astimezone(ZoneInfo(user.timezone)).replace(hour=12)
    for i in range(3):
        p = Problem.objects.create(
            platform="cses",
            problem_id=str(i),
            title=f"P{i}",
            url=f"https://cses.fi/problemset/task/{i}",
        )
        JournalEntry.objects.create(user=user, problem=p, solved_at=now - timedelta(days=i))
    with patch("apps.journal.services.timezone.now", return_value=now):
        stats = analytics(user)
    assert stats["streak"] == 3 and stats["total"] == 3
