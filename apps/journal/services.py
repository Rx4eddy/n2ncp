from collections import Counter
from datetime import timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import JournalEntry


def canonical_problem_url(value):
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise ValidationError(
            "Use a public HTTPS problem URL without credentials or a custom port."
        )
    host, path = (parsed.hostname or "").lower(), parsed.path.rstrip("/")
    import re

    patterns = [
        (
            {"codeforces.com", "www.codeforces.com"},
            r"/(?:problemset/problem|contest)/(\d+)/(?:problem/)?([A-Za-z0-9]+)",
            "codeforces",
            lambda m: (
                m[1] + m[2].upper(),
                f"https://codeforces.com/problemset/problem/{m[1]}/{m[2].upper()}",
            ),
        ),
        (
            {"atcoder.jp"},
            r"/contests/([A-Za-z0-9_-]+)/tasks/([A-Za-z0-9_-]+)",
            "atcoder",
            lambda m: (m[2], f"https://atcoder.jp/contests/{m[1]}/tasks/{m[2]}"),
        ),
        (
            {"cses.fi"},
            r"/problemset/task/(\d+)",
            "cses",
            lambda m: (m[1], f"https://cses.fi/problemset/task/{m[1]}"),
        ),
        (
            {"codechef.com", "www.codechef.com"},
            r"/(?:[A-Za-z0-9_-]+/)?problems/([A-Za-z0-9_]+)",
            "codechef",
            lambda m: (m[1].upper(), f"https://www.codechef.com/problems/{m[1].upper()}"),
        ),
        (
            {"leetcode.com", "www.leetcode.com"},
            r"/problems/([a-z0-9-]+)(?:/description)?",
            "leetcode",
            lambda m: (m[1], f"https://leetcode.com/problems/{m[1]}/"),
        ),
    ]
    for hosts, pattern, platform, convert in patterns:
        match = re.fullmatch(pattern, path)
        if host in hosts and match:
            pid, url = convert(match)
            return platform, pid, url
    raise ValidationError("Use a Codeforces, AtCoder, CSES, CodeChef, or LeetCode problem link.")


def analytics(user):
    entries = (
        JournalEntry.objects.filter(user=user)
        .select_related("problem")
        .prefetch_related("problem__topics")
    )
    days, platforms, topics = Counter(), Counter(), Counter()
    zone = ZoneInfo(user.timezone)
    for entry in entries:
        days[entry.solved_at.astimezone(zone).date()] += 1
        platforms[entry.problem.platform] += 1
        for topic in entry.problem.topics.all():
            topics[topic.name] += 1
    today = timezone.now().astimezone(zone).date()
    cursor = today if days[today] else today - timedelta(days=1)
    streak = 0
    while days[cursor]:
        streak += 1
        cursor -= timedelta(days=1)
    start = today - timedelta(days=181)
    heatmap = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "count": days[start + timedelta(days=i)],
            "level": min(4, days[start + timedelta(days=i)]),
        }
        for i in range(182)
    ]
    return {
        "total": len(entries),
        "streak": streak,
        "today": days[today],
        "heatmap": heatmap,
        "platforms": dict(platforms),
        "topics": dict(topics),
    }
