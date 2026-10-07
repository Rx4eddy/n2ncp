from datetime import UTC, datetime

from .base import Adapter, PlatformError, SolvedProblem


class Codeforces(Adapter):
    key = "codeforces"
    allowed_hosts = frozenset({"codeforces.com"})
    can_link = can_sync = can_contests = True
    verification_field = "first name or last name in your public Codeforces profile"

    def api(self, method, **params):
        data = self.fetch(f"https://codeforces.com/api/{method}", params=params)
        if data.get("status") != "OK":
            raise PlatformError("Codeforces could not process the request")
        return data["result"]

    def fetch_public_profile(self, handle):
        user = self.api("user.info", handles=handle)[0]
        return " ".join(user.get(key, "") for key in ["firstName", "lastName"])

    def fetch_contests(self):
        return [
            {
                "external_id": str(c["id"]),
                "title": c["name"],
                "url": f"https://codeforces.com/contest/{c['id']}",
                "start_at": datetime.fromtimestamp(c["startTimeSeconds"], UTC),
                "duration_seconds": c["durationSeconds"],
            }
            for c in self.api("contest.list", gym="false")
            if c.get("phase") == "BEFORE" and "startTimeSeconds" in c
        ]

    def fetch_solved_problems(self, handle, cursor):
        offset = cursor.get("offset", 1)
        submissions = self.api("user.status", handle=handle, **{"from": offset, "count": 1000})
        solved = []
        for submission in submissions:
            if submission.get("verdict") != "OK":
                continue
            p = submission["problem"]
            if "contestId" not in p:
                continue
            pid = f"{p['contestId']}{p['index']}"
            solved.append(
                SolvedProblem(
                    pid,
                    p["name"],
                    f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}",
                    self.key,
                    datetime.fromtimestamp(submission["creationTimeSeconds"], UTC),
                    tags=p.get("tags", []),
                    difficulty=max(1, min(5, (p.get("rating", 800) - 400) // 500)),
                )
            )
        return solved, {"offset": offset + len(submissions) if len(submissions) == 1000 else 1}
