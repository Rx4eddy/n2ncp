from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from apps.journal.models import JournalEntry
from apps.practice.models import Attempt, ExerciseProgress, Module, ProblemReview

from .models import Problem


def completed_modules(user):
    progress = set(
        ExerciseProgress.objects.filter(user=user, completed_at__isnull=False).values_list(
            "exercise_id", flat=True
        )
    )
    completed = set()
    for module in Module.objects.prefetch_related("exercises"):
        ids = {exercise.pk for exercise in module.exercises.all()}
        if ids and len(ids & progress) >= max(1, (len(ids) * 3 + 4) // 5):
            completed.add(module.pk)
    return completed


def recommend(user, topic=None, platform=None, mode="learn", limit=12):
    solved = JournalEntry.objects.filter(user=user)
    solved_ids = solved.values_list("problem_id", flat=True)
    problems = (
        Problem.objects.filter(curated=True).exclude(pk__in=solved_ids).prefetch_related("topics")
    )
    if topic:
        problems = problems.filter(topics__slug=topic)
    if platform:
        problems = problems.filter(platform=platform)
    evidence = defaultdict(lambda: {"independent": 0, "struggled": 0, "hinted": 0})
    # Cap repeated attempts per problem to the most recent outcome, so clicking
    # repeatedly cannot manufacture mastery or weakness.
    seen = set()
    attempts = (
        Attempt.objects.filter(user=user, problem__isnull=False)
        .select_related("problem")
        .prefetch_related("problem__topics")
        .order_by("-created_at")
    )
    for attempt in attempts:
        if attempt.problem_id in seen:
            continue
        seen.add(attempt.problem_id)
        for tag in attempt.problem.topics.all():
            evidence[tag.slug][attempt.outcome] += 1
    completed = completed_modules(user)
    modules = list(Module.objects.prefetch_related("topics", "prerequisites"))
    ready_topics = set()
    for module in modules:
        if all(p.pk in completed for p in module.prerequisites.all()):
            ready_topics.update(t.slug for t in module.topics.all())
    baseline = {"beginner": 1, "intermediate": 2, "advanced": 3}[user.experience]
    ranked = []
    for problem in problems.distinct():
        tags = [tag.slug for tag in problem.topics.all()]
        ready = (bool(tags) and set(tags).issubset(ready_topics)) or not modules
        # An explicit topic filter lets users deliberately explore ahead.
        if not ready and not topic:
            continue
        independent = max((evidence[t]["independent"] for t in tags), default=0)
        struggles = max((evidence[t]["struggled"] + evidence[t]["hinted"] for t in tags), default=0)
        target = min(5, baseline + independent // 3 + (mode == "challenge"))
        score = 50 - abs(problem.difficulty - target) * 15
        reasons = [f"Difficulty {problem.difficulty}/5 fits your current target of {target}/5."]
        if struggles:
            score += min(struggles, 3) * (10 if mode == "weak" else 4)
            reasons.append("Reinforces a pattern where you recently needed help.")
        elif independent:
            reasons.append("Builds on patterns you have solved independently.")
        else:
            reasons.append("Introduces a pattern on your learning path.")
        if mode == "weak" and not struggles:
            score -= 20
        if not ready:
            reasons.append("You are exploring ahead of the suggested prerequisites.")
        ranked.append({"problem": problem, "score": score, "reason": " ".join(reasons)})
    ranked.sort(key=lambda r: (-r["score"], r["problem"].difficulty, r["problem"].pk))
    # Diversify the top selection without hiding relevant focused-topic results.
    selected, platform_counts = [], defaultdict(int)
    while ranked and len(selected) < limit:
        best = max(ranked, key=lambda r: r["score"] - platform_counts[r["problem"].platform] * 4)
        ranked.remove(best)
        selected.append(best)
        platform_counts[best["problem"].platform] += 1
    return selected


def due_reviews(user):
    return (
        ProblemReview.objects.filter(user=user, next_review_at__lte=timezone.now())
        .select_related("problem")
        .order_by("next_review_at")[:12]
    )


def record_problem_attempt(user, problem, outcome):
    from django.db import transaction

    with transaction.atomic():
        Attempt.objects.create(user=user, problem=problem, outcome=outcome)
        if outcome in {"independent", "hinted"}:
            JournalEntry.objects.get_or_create(
                user=user,
                problem=problem,
                defaults={"solved_at": timezone.now(), "independent": outcome == "independent"},
            )
        review, _ = ProblemReview.objects.select_for_update().get_or_create(
            user=user, problem=problem, defaults={"next_review_at": timezone.now()}
        )
        review.level = min(5, review.level + 1) if outcome == "independent" else 0
        review.next_review_at = timezone.now() + timedelta(days=[1, 3, 7, 14, 30, 60][review.level])
        review.save()
