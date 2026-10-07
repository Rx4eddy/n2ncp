from django.conf import settings
from django.db import models
from django.utils import timezone


class ReminderPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=24)
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "platform"], name="unique_reminder_preference")
        ]


class ReminderDelivery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contest = models.ForeignKey("contests.Contest", on_delete=models.CASCADE)
    kind = models.CharField(
        max_length=12, choices=[("morning", "Morning"), ("before", "Two hours before")]
    )
    due_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "contest", "kind"], name="unique_reminder")
        ]


class EmailOutbox(models.Model):
    reminder = models.OneToOneField(
        ReminderDelivery, null=True, blank=True, on_delete=models.CASCADE
    )
    recipient = models.EmailField()
    subject = models.CharField(max_length=300)
    body = models.TextField()
    headers = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16,
        default="pending",
        choices=[
            (s, s) for s in ["pending", "sending", "sent", "cancelled", "uncertain", "failed"]
        ],
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    claimed_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_error = models.CharField(max_length=200, blank=True)
