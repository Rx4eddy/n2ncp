from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from apps.contests.models import Contest
from apps.contests.tasks import sync_contests
from apps.journal.models import JournalEntry
from apps.platforms.adapters import ADAPTERS
from apps.platforms.adapters.base import PlatformError, SolvedProblem
from apps.platforms.models import LinkedAccount, SyncRun
from apps.platforms.tasks import sync_account

pytestmark = pytest.mark.django_db


def test_platform_failure_does_not_remove_other_contests(monkeypatch):
    def fail():
        raise PlatformError("offline")

    monkeypatch.setattr(ADAPTERS["atcoder"], "fetch_contests", fail)
    with patch.object(sync_contests, "retry", side_effect=Retry), pytest.raises(Retry):
        sync_contests("atcoder")
    row = {
        "external_id": "10",
        "title": "Example round",
        "url": "https://codeforces.com/contest/10",
        "start_at": datetime(2027, 1, 1, tzinfo=UTC),
        "duration_seconds": 7200,
    }
    monkeypatch.setattr(ADAPTERS["codeforces"], "fetch_contests", lambda: [dict(row)])
    sync_contests("codeforces")
    sync_contests("codeforces")
    assert Contest.objects.count() == 1
    assert not SyncRun.objects.get(platform="atcoder").success
    assert SyncRun.objects.filter(platform="codeforces", success=True).count() == 2


def test_import_is_idempotent_preserves_notes_and_maps_tags(user, monkeypatch):
    account = LinkedAccount.objects.create(
        user=user, platform="codeforces", handle="learner", verified_at=timezone.now()
    )
    item = SolvedProblem(
        "4A",
        "Watermelon",
        "https://codeforces.com/problemset/problem/4/A",
        "codeforces",
        datetime(2025, 1, 1, tzinfo=UTC),
        tags=["math"],
    )
    monkeypatch.setattr(
        ADAPTERS["codeforces"], "fetch_solved_problems", lambda *a: ([item], {"offset": 1})
    )
    sync_account(account.pk)
    entry = JournalEntry.objects.get(user=user)
    entry.notes = "My own insight"
    entry.save()
    sync_account(account.pk)
    entry.refresh_from_db()
    assert JournalEntry.objects.count() == 1
    assert entry.notes == "My own insight"
    assert entry.problem.topics.get().slug == "math"
    account.refresh_from_db()
    assert account.last_synced_at
