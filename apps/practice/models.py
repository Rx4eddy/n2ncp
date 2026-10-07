from django.conf import settings
from django.db import models


class Module(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField()
    description = models.TextField()
    recognition = models.TextField()
    pitfalls = models.TextField()
    cpp_example = models.TextField()
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True)
    topics = models.ManyToManyField("recommendations.Topic")

    class Meta:
        ordering = ["order"]


class Exercise(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="exercises")
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    prompt = models.TextField()
    hints = models.JSONField(default=list)
    solution = models.TextField()
    order = models.PositiveSmallIntegerField()
    problem = models.ForeignKey(
        "recommendations.Problem", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["module", "slug"], name="unique_exercise")]


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem = models.ForeignKey(
        "recommendations.Problem", null=True, blank=True, on_delete=models.CASCADE
    )
    exercise = models.ForeignKey(Exercise, null=True, blank=True, on_delete=models.CASCADE)
    outcome = models.CharField(
        max_length=16,
        choices=[
            ("struggled", "Still working"),
            ("hinted", "Solved with help"),
            ("independent", "Solved independently"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(problem__isnull=False, exercise__isnull=True)
                    | models.Q(problem__isnull=True, exercise__isnull=False)
                ),
                name="attempt_has_one_target",
            )
        ]


class ExerciseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(null=True)
    next_review_at = models.DateTimeField(null=True, db_index=True)
    review_level = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "exercise"], name="unique_exercise_progress")
        ]


class ProblemReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem = models.ForeignKey("recommendations.Problem", on_delete=models.CASCADE)
    next_review_at = models.DateTimeField(db_index=True)
    level = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "problem"], name="unique_problem_review")
        ]
