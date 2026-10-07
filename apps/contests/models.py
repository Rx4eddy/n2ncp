from django.db import models


class Contest(models.Model):
    platform = models.CharField(max_length=24, db_index=True)
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    url = models.URLField(max_length=500)
    start_at = models.DateTimeField(db_index=True)
    duration_seconds = models.PositiveIntegerField()
    cancelled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.UniqueConstraint(fields=["platform", "external_id"], name="unique_contest")
        ]

    @property
    def duration_minutes(self):
        return self.duration_seconds // 60
