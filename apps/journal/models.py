from django.conf import settings
from django.db import models


class JournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem = models.ForeignKey("recommendations.Problem", on_delete=models.PROTECT)
    solved_at = models.DateTimeField(db_index=True)
    verdict = models.CharField(max_length=32, default="AC")
    notes = models.TextField(blank=True, max_length=10000)
    source = models.CharField(max_length=16, default="manual")
    independent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-solved_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "problem"], name="one_solve_per_problem")
        ]
