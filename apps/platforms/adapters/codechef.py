from datetime import datetime

from .base import Adapter, PlatformError


class CodeChef(Adapter):
    key = "codechef"
    allowed_hosts = frozenset({"www.codechef.com"})
    can_contests = True
    limitation = "Verified linking and solve import are disabled until a reliable public bio and submissions source is available. Use manual journal entries."

    def fetch_contests(self):
        data = self.fetch("https://www.codechef.com/api/list/contests/all")
        if "future_contests" not in data:
            raise PlatformError("CodeChef contest response changed")
        contests = []
        for row in data["future_contests"]:
            start = datetime.fromisoformat(
                row.get("contest_start_date_iso") or row["contest_start_date"]
            )
            end = datetime.fromisoformat(row.get("contest_end_date_iso") or row["contest_end_date"])
            if start.tzinfo is None or end.tzinfo is None:
                from zoneinfo import ZoneInfo

                start, end = (
                    start.replace(tzinfo=ZoneInfo("Asia/Kolkata")),
                    end.replace(tzinfo=ZoneInfo("Asia/Kolkata")),
                )
            contests.append(
                {
                    "external_id": row["contest_code"],
                    "title": row["contest_name"],
                    "url": f"https://www.codechef.com/{row['contest_code']}",
                    "start_at": start,
                    "duration_seconds": int((end - start).total_seconds()),
                }
            )
        return contests
