from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.recommendations.models import Problem
from apps.recommendations.services import (
    completed_modules,
    due_reviews,
    record_problem_attempt,
)

from .models import Attempt, Exercise, ExerciseProgress, Module


@login_required
def practice(request):
    completed = completed_modules(request.user)
    modules = list(Module.objects.prefetch_related("prerequisites", "exercises"))
    for module in modules:
        module.done = module.pk in completed
        module.ready = all(p.pk in completed for p in module.prerequisites.all())
    return render(
        request,
        "practice/index.html",
        {
            "modules": modules,
            "completed_count": len(completed),
            "reviews": due_reviews(request.user),
            "exercise_reviews": ExerciseProgress.objects.filter(
                user=request.user, next_review_at__lte=timezone.now()
            ).select_related("exercise__module")[:12],
        },
    )


@login_required
def module_detail(request, slug):
    module = get_object_or_404(
        Module.objects.prefetch_related("exercises__problem", "prerequisites"), slug=slug
    )
    done = set(
        ExerciseProgress.objects.filter(user=request.user, completed_at__isnull=False).values_list(
            "exercise_id", flat=True
        )
    )
    return render(request, "practice/module.html", {"module": module, "done": done})


@login_required
@require_POST
@ratelimit(key="user", rate="60/h", block=True)
def attempt(request):
    outcome = request.POST.get("outcome")
    if outcome not in {"struggled", "hinted", "independent"}:
        return HttpResponseBadRequest("Invalid attempt outcome")
    target = request.POST.get("exercise") or request.POST.get("problem", "")
    if not target.isdecimal() or len(target) > 15:
        return HttpResponseBadRequest("Invalid practice target")
    if request.POST.get("exercise"):
        exercise = get_object_or_404(Exercise, pk=request.POST["exercise"])
        with transaction.atomic():
            Attempt.objects.create(user=request.user, exercise=exercise, outcome=outcome)
            progress, _ = ExerciseProgress.objects.select_for_update().get_or_create(
                user=request.user, exercise=exercise
            )
            if outcome != "struggled":
                progress.completed_at = timezone.now()
            progress.review_level = (
                min(5, progress.review_level + 1) if outcome == "independent" else 0
            )
            progress.next_review_at = timezone.now() + timedelta(
                days=[1, 3, 7, 14, 30, 60][progress.review_level]
            )
            progress.save()
            if exercise.problem:
                record_problem_attempt(request.user, exercise.problem, outcome)
        messages.success(request, "Practice recorded. Your next review has been scheduled.")
        return redirect("module", slug=exercise.module.slug)
    problem = get_object_or_404(Problem, pk=request.POST.get("problem"))
    record_problem_attempt(request.user, problem, outcome)
    messages.success(request, "Attempt recorded. Your recommendations have been updated.")
    return redirect("recommendations")
