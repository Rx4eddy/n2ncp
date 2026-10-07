from django.db import models


class Topic(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Problem(models.Model):
    platform = models.CharField(max_length=24)
    problem_id = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    url = models.URLField(max_length=500)
    difficulty = models.PositiveSmallIntegerField(default=1)
    topics = models.ManyToManyField(Topic, related_name="problems")
    curated = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["platform", "problem_id"], name="unique_problem"),
            models.CheckConstraint(
                condition=models.Q(difficulty__gte=1, difficulty__lte=5), name="valid_difficulty"
            ),
        ]
        ordering = ["difficulty", "title"]

    def __str__(self):
        return self.title
