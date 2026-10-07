from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class LinkedAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=24)
    handle = models.CharField(max_length=64)
    verified_at = models.DateTimeField()
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_cursor = models.JSONField(default=dict)
    status = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "platform"], name="one_account_per_platform"),
            models.UniqueConstraint(Lower("handle"), "platform", name="one_owner_per_handle"),
        ]


class OwnershipChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=24)
    handle = models.CharField(max_length=64)
    token_digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SyncRun(models.Model):
    platform = models.CharField(max_length=24)
    kind = models.CharField(max_length=24)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    success = models.BooleanField(default=False)
    detail = models.CharField(max_length=300, blank=True)
