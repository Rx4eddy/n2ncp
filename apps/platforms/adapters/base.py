from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import requests
from django.core.cache import cache


class PlatformError(Exception):
    pass


@dataclass
class SolvedProblem:
    problem_id: str
    title: str
    url: str
    platform: str
    solved_date: datetime
    verdict: str = "AC"
    tags: list[str] = field(default_factory=list)
    difficulty: int = 1


class Adapter:
    key = ""
    allowed_hosts = frozenset()
    can_link = False
    can_sync = False
    can_contests = False
    verification_field = ""
    limitation = ""

    def fetch(self, url, params=None, json=True):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise PlatformError("Untrusted upstream destination")
        cooldown = 2 if parsed.hostname == "codeforces.com" else 1
        if not cache.add(f"upstream-rate:{parsed.hostname}", True, cooldown):
            raise PlatformError("Upstream request cooldown; try again shortly")
        try:
            with requests.get(
                url,
                params=params,
                timeout=(5, 20),
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "n2ncp/1.0 (public contest and profile reader)"},
            ) as response:
                if response.status_code != 200:
                    raise PlatformError(f"Upstream returned HTTP {response.status_code}")
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > 8_000_000:
                        raise PlatformError("Upstream response too large")
                text = content.decode("utf-8")
                if json:
                    import json as json_module

                    return json_module.loads(text)
                return text
        except (requests.RequestException, ValueError, UnicodeError) as exc:
            raise PlatformError(f"Upstream unavailable ({type(exc).__name__})") from exc

    def fetch_public_profile(self, handle):
        raise PlatformError(self.limitation or "Public profile verification is unavailable")

    def fetch_solved_problems(self, handle, cursor):
        raise PlatformError(self.limitation or "Solve import is unavailable")

    def fetch_contests(self):
        raise PlatformError("Contest import is unavailable")
