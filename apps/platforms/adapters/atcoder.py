from datetime import UTC, datetime
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import Adapter, PlatformError, SolvedProblem


class AtCoder(Adapter):
    key = "atcoder"
    allowed_hosts = frozenset({"atcoder.jp", "kenkoooo.com"})
    can_link = can_sync = can_contests = True
    verification_field = "Affiliation field of your public AtCoder profile"
    limitation = "Solve import uses the community AtCoder Problems API, which may lag."

    def fetch_public_profile(self, handle):
        soup = BeautifulSoup(
            self.fetch(f"https://atcoder.jp/users/{quote(handle, safe='')}", json=False),
            "html.parser",
        )
        for row in soup.select("table tr"):
            heading, value = row.find("th"), row.find("td")
            if heading and value and heading.get_text(strip=True) in {"Affiliation", "所属"}:
                return value.get_text(" ", strip=True)
        return ""

    def fetch_contests(self):
        soup = BeautifulSoup(
            self.fetch("https://atcoder.jp/contests/?lang=en", json=False), "html.parser"
        )
        table = soup.select_one("#contest-table-upcoming")
        if table is None:
            raise PlatformError("AtCoder schedule markup changed")
        contests = []
        for row in table.select("tbody tr"):
            cells = row.find_all("td")
            link, time = row.select_one('a[href^="/contests/"]'), row.find("time")
            if link and time and len(cells) >= 3:
                hours, minutes = map(int, cells[2].get_text(strip=True).split(":"))
                contests.append(
                    {
                        "external_id": link["href"].rstrip("/").split("/")[-1],
                        "title": link.get_text(strip=True),
                        "url": "https://atcoder.jp" + link["href"],
                        "start_at": datetime.strptime(
                            time.get_text(strip=True), "%Y-%m-%d %H:%M:%S%z"
                        ),
                        "duration_seconds": hours * 3600 + minutes * 60,
                    }
                )
        return contests

    def fetch_solved_problems(self, handle, cursor):
        rows = self.fetch(
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions",
            params={"user": handle, "from_second": cursor.get("from_second", 0)},
        )
        solved = [
            SolvedProblem(
                r["problem_id"],
                r["problem_id"].replace("_", " ").title(),
                f"https://atcoder.jp/contests/{r['contest_id']}/tasks/{r['problem_id']}",
                self.key,
                datetime.fromtimestamp(r["epoch_second"], UTC),
            )
            for r in rows
            if r["result"] == "AC"
        ]
        latest = max((r["epoch_second"] for r in rows), default=cursor.get("from_second", 0) - 1)
        return solved, {"from_second": latest + 1}
