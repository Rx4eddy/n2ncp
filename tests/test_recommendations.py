from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.journal.models import JournalEntry
from apps.practice.models import Attempt, ExerciseProgress, Module, ProblemReview
from apps.recommendations.models import Problem, Topic
from apps.recommendations.services import (
    completed_modules,
    due_reviews,
    recommend,
    record_problem_attempt,
)

pytestmark = pytest.mark.django_db


def problem(pid, difficulty=1, topic="arrays", platform="codeforces"):
    p = Problem.objects.create(
        platform=platform,
        problem_id=pid,
        title=f"Problem {pid}",
        url=f"https://codeforces.com/problemset/problem/1/{pid}",
        difficulty=difficulty,
        curated=True,
    )
    p.topics.add(Topic.objects.get_or_create(slug=topic, defaults={"name": topic})[0])
    return p


def test_hides_solved_and_filters(user):
    solved, wanted = problem("A"), problem("B")
    problem("C", topic="graphs")
    JournalEntry.objects.create(user=user, problem=solved, solved_at=timezone.now())
    assert [r["problem"] for r in recommend(user, topic="arrays")] == [wanted]


def test_cold_start_prefers_easy_and_explains(user):
    easy = problem("A", 1)
    problem("B", 4)
    rows = recommend(user)
    assert rows[0]["problem"] == easy
    assert "target of 1" in rows[0]["reason"]


def test_independent_attempts_increase_target(user):
    for i in range(3):
        p = problem(str(i))
        record_problem_attempt(user, p, "independent")
    problem("easy", 1)
    target = problem("medium", 2)
    assert recommend(user)[0]["problem"] == target


def test_repeated_attempts_do_not_inflate_mastery(user):
    p = problem("A")
    for _ in range(10):
        Attempt.objects.create(user=user, problem=p, outcome="independent")
    rows = recommend(user)
    assert all("target of 1" in row["reason"] for row in rows)


def test_imported_solve_is_not_mastery(user):
    for i in range(4):
        p = problem(str(i), 3)
        JournalEntry.objects.create(user=user, problem=p, solved_at=timezone.now(), source="import")
    problem("new", 1)
    assert "target of 1" in recommend(user)[0]["reason"]


def test_weak_pattern_prioritized(user):
    p = problem("attempt", topic="graphs")
    Attempt.objects.create(user=user, problem=p, outcome="struggled")
    problem("normal", topic="arrays")
    rows = recommend(user, mode="weak")
    assert rows[0]["problem"] == p
    assert "needed help" in rows[0]["reason"]


def test_reviews_separate_from_new_recommendations(user):
    p = problem("A")
    record_problem_attempt(user, p, "independent")
    assert recommend(user) == []
    ProblemReview.objects.filter(user=user).update(
        next_review_at=timezone.now() - timedelta(days=1)
    )
    assert list(due_reviews(user))[0].problem == p


def test_seed_is_idempotent_and_static_leetcode(seeded, monkeypatch):
    import requests

    monkeypatch.setattr(
        requests, "get", lambda *a, **k: pytest.fail("Seed must never access the network")
    )
    before = Problem.objects.count()
    call_command("seed", verbosity=0)
    assert Problem.objects.count() == before >= 150
    assert Problem.objects.filter(platform="leetcode").count() >= 20
    assert Module.objects.count() == 32


def test_prerequisite_gate(user, seeded):
    assert all(
        "dp" not in [t.slug for t in r["problem"].topics.all()] for r in recommend(user, limit=100)
    )
    module = Module.objects.get(slug="cpp-stl")
    for exercise in module.exercises.all():
        ExerciseProgress.objects.create(user=user, exercise=exercise, completed_at=timezone.now())
    assert module.pk in completed_modules(user)
    # Deliberate exploration is always available with a topic filter.
    assert recommend(user, topic="dp")


def test_seed_field_lengths_and_curriculum_dag(seeded):
    from apps.practice.models import Exercise

    for exercise in Exercise.objects.all():
        exercise.full_clean()
    visited, active = set(), set()

    def visit(module):
        assert module.pk not in active, "Prerequisites contain a cycle"
        if module.pk in visited:
            return
        active.add(module.pk)
        for previous in module.prerequisites.all():
            visit(previous)
        active.remove(module.pk)
        visited.add(module.pk)

    for module in Module.objects.all():
        visit(module)


def test_review_keeps_original_solve_date(user):
    p = problem("A")
    original = timezone.now() - timedelta(days=30)
    JournalEntry.objects.create(user=user, problem=p, solved_at=original)
    record_problem_attempt(user, p, "independent")
    assert JournalEntry.objects.get(user=user, problem=p).solved_at == original
