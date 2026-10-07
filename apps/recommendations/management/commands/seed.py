import json
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.practice.models import Exercise, Module
from apps.recommendations.models import Problem, Topic

PLATFORM_HOSTS = {
    "codeforces": "codeforces.com",
    "atcoder": "atcoder.jp",
    "codechef": "www.codechef.com",
    "cses": "cses.fi",
    "leetcode": "leetcode.com",
}


class Command(BaseCommand):
    help = "Idempotently import the reviewed, offline problem bank and practice curriculum."

    def add_arguments(self, parser):
        parser.add_argument(
            "--problems", type=Path, default=settings.BASE_DIR / "data/problems.json"
        )
        parser.add_argument(
            "--curriculum", type=Path, default=settings.BASE_DIR / "data/curriculum.json"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        problems = json.loads(options["problems"].read_text())
        curriculum = json.loads(options["curriculum"].read_text())
        seen = set()
        for row in problems:
            key = row["platform"], row["problem_id"]
            url = urlparse(row["url"])
            if (
                key in seen
                or not 1 <= row["difficulty"] <= 5
                or url.scheme != "https"
                or url.hostname != PLATFORM_HOSTS.get(row["platform"])
                or not row["topics"]
            ):
                raise CommandError(f"Invalid problem entry: {key}")
            seen.add(key)
            problem, _ = Problem.objects.update_or_create(
                platform=row["platform"],
                problem_id=row["problem_id"],
                defaults={k: row[k] for k in ["title", "url", "difficulty"]} | {"curated": True},
            )
            problem.topics.set(
                [
                    Topic.objects.get_or_create(
                        slug=t, defaults={"name": t.replace("-", " ").title()}
                    )[0]
                    for t in row["topics"]
                ]
            )
        for row in curriculum:
            module, _ = Module.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    k: row[k]
                    for k in [
                        "title",
                        "order",
                        "description",
                        "recognition",
                        "pitfalls",
                        "cpp_example",
                    ]
                },
            )
            module.topics.set(
                [
                    Topic.objects.get_or_create(
                        slug=t, defaults={"name": t.replace("-", " ").title()}
                    )[0]
                    for t in row["topics"]
                ]
            )
            for index, exercise in enumerate(row["exercises"], 1):
                Exercise.objects.update_or_create(
                    module=module,
                    slug=exercise["slug"],
                    defaults={k: exercise[k] for k in ["title", "prompt", "hints", "solution"]}
                    | {"order": index},
                )
            candidates = (
                Problem.objects.filter(curated=True, topics__slug__in=row["topics"])
                .distinct()
                .order_by("difficulty", "title")[:6]
            )
            for index, problem in enumerate(candidates, len(row["exercises"]) + 1):
                Exercise.objects.update_or_create(
                    module=module,
                    slug=f"{problem.platform}-{problem.problem_id}",
                    defaults={
                        "title": problem.title,
                        "problem": problem,
                        "order": index,
                        "prompt": f"Apply this module to {problem.title}. Read the full statement on {problem.platform.title()}, derive a solution, and test boundary cases before submitting. Then record whether you needed help.",
                        "hints": [
                            row["recognition"],
                            "Write a small brute-force reference first. Identify the repeated work or invariant before optimizing.",
                        ],
                        "solution": f"Reflection checklist: state your invariant, justify correctness, and calculate time and space complexity. {row['pitfalls']} These are pattern prompts, not a problem-specific editorial.",
                    },
                )
        for row in curriculum:
            Module.objects.get(slug=row["slug"]).prerequisites.set(
                [Module.objects.get(slug=s) for s in row["prerequisites"]]
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(problems)} curated problems and {len(curriculum)} practice modules."
            )
        )
