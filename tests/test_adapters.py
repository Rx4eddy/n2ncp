from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from apps.platforms.adapters import ADAPTERS, get_adapter
from apps.platforms.adapters.atcoder import AtCoder
from apps.platforms.adapters.base import PlatformError
from apps.platforms.adapters.codechef import CodeChef
from apps.platforms.adapters.codeforces import Codeforces
from apps.platforms.models import LinkedAccount, OwnershipChallenge
from apps.platforms.services import create_challenge, verify_challenge


def test_leetcode_never_has_adapter():
    assert "leetcode" not in ADAPTERS
    with pytest.raises(PlatformError):
        get_adapter("leetcode")


def test_adapter_blocks_untrusted_destinations():
    for url in [
        "https://leetcode.com/api",
        "http://codeforces.com/api",
        "https://127.0.0.1/",
        "https://codeforces.com.evil.test/",
    ]:
        with pytest.raises(PlatformError):
            Codeforces().fetch(url)


def test_codeforces_normalizes_accepted_only(monkeypatch):
    adapter = Codeforces()
    monkeypatch.setattr(
        adapter,
        "api",
        lambda *a, **k: [
            {
                "verdict": "OK",
                "creationTimeSeconds": 1700000000,
                "problem": {
                    "contestId": 4,
                    "index": "A",
                    "name": "Watermelon",
                    "tags": ["math"],
                    "rating": 800,
                },
            },
            {"verdict": "WRONG_ANSWER", "problem": {}},
        ],
    )
    rows, cursor = adapter.fetch_solved_problems("tourist", {})
    assert len(rows) == 1
    assert rows[0].problem_id == "4A"
    assert rows[0].solved_date.tzinfo == UTC
    assert rows[0].tags == ["math"]
    assert cursor == {"offset": 1}


def test_cf_api_error(monkeypatch):
    adapter = Codeforces()
    monkeypatch.setattr(adapter, "fetch", lambda *a, **kw: {"status": "FAILED"})
    with pytest.raises(PlatformError):
        adapter.fetch_contests()


def test_cf_upcoming_only(monkeypatch):
    adapter = Codeforces()
    monkeypatch.setattr(
        adapter,
        "api",
        lambda *a, **kw: [
            {
                "id": 7,
                "name": "Round",
                "phase": "BEFORE",
                "startTimeSeconds": 1700000000,
                "durationSeconds": 7200,
            },
            {"phase": "FINISHED"},
        ],
    )
    assert len(adapter.fetch_contests()) == 1


def test_atcoder_profile_and_contest_parse(monkeypatch):
    adapter = AtCoder()
    monkeypatch.setattr(
        adapter,
        "fetch",
        lambda *a, **k: "<table><tr><th>Affiliation</th><td>team n2ncp-abc</td></tr></table>",
    )
    assert adapter.fetch_public_profile("learner") == "team n2ncp-abc"
    html = '<div id="contest-table-upcoming"><table><tbody><tr><td><time>2026-10-10 21:00:00+0900</time></td><td><a href="/contests/abc400">ABC 400</a></td><td>01:40</td></tr></tbody></table></div>'
    monkeypatch.setattr(adapter, "fetch", lambda *a, **k: html)
    rows = adapter.fetch_contests()
    assert rows[0]["external_id"] == "abc400"
    assert rows[0]["duration_seconds"] == 6000
    assert rows[0]["start_at"].hour == 21


def test_atcoder_markup_failure_is_explicit(monkeypatch):
    monkeypatch.setattr(AtCoder, "fetch", lambda *a, **k: "<html>challenge</html>")
    with pytest.raises(PlatformError):
        AtCoder().fetch_contests()


def test_atcoder_cursor_and_acceptance(monkeypatch):
    monkeypatch.setattr(
        AtCoder,
        "fetch",
        lambda *a, **k: [
            {"problem_id": "dp_a", "contest_id": "dp", "result": "AC", "epoch_second": 100},
            {"problem_id": "dp_b", "contest_id": "dp", "result": "WA", "epoch_second": 101},
        ],
    )
    rows, cursor = AtCoder().fetch_solved_problems("learner", {})
    assert len(rows) == 1 and cursor == {"from_second": 102}


def test_codechef_timezone(monkeypatch):
    monkeypatch.setattr(
        CodeChef,
        "fetch",
        lambda *a, **k: {
            "future_contests": [
                {
                    "contest_code": "START1",
                    "contest_name": "Starters",
                    "contest_start_date": "2026-10-10 20:00:00",
                    "contest_end_date": "2026-10-10 22:00:00",
                }
            ]
        },
    )
    row = CodeChef().fetch_contests()[0]
    assert row["duration_seconds"] == 7200
    assert row["start_at"].utcoffset().total_seconds() == 19800


@pytest.mark.django_db
def test_verification_requires_token_and_consumes_challenge(user, monkeypatch):
    challenge, token = create_challenge(user, "codeforces", "tourist")
    assert token not in challenge.token_digest
    monkeypatch.setattr(Codeforces, "fetch_public_profile", lambda *a: "unrelated token")
    with pytest.raises(ValidationError):
        verify_challenge(user, challenge.pk)
    monkeypatch.setattr(Codeforces, "fetch_public_profile", lambda *a: f"Hello {token}")
    account = verify_challenge(user, challenge.pk)
    assert account.handle == "tourist"
    with pytest.raises(OwnershipChallenge.DoesNotExist):
        verify_challenge(user, challenge.pk)


@pytest.mark.django_db
def test_expired_challenge_cannot_verify(user, monkeypatch):
    challenge, token = create_challenge(user, "atcoder", "learner")
    challenge.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
    challenge.save()
    spy = Mock()
    monkeypatch.setattr(AtCoder, "fetch_public_profile", spy)
    with pytest.raises(OwnershipChallenge.DoesNotExist):
        verify_challenge(user, challenge.pk)
    spy.assert_not_called()


@pytest.mark.django_db
def test_unsupported_linking_never_requests_password(user):
    for platform in ["codechef", "cses"]:
        with pytest.raises(ValidationError):
            create_challenge(user, platform, "someone")
    with pytest.raises(PlatformError):
        create_challenge(user, "leetcode", "someone")
    assert LinkedAccount.objects.count() == 0
