import hashlib
import re
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .adapters import get_adapter
from .models import LinkedAccount, OwnershipChallenge


def create_challenge(user, platform, handle):
    adapter = get_adapter(platform)
    if not adapter.can_link:
        raise ValidationError(adapter.limitation)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", handle):
        raise ValidationError(
            "Handle may contain letters, numbers, underscores, periods, and hyphens."
        )
    token = "n2ncp-" + secrets.token_hex(10)
    with transaction.atomic():
        OwnershipChallenge.objects.filter(
            user=user, platform=platform, consumed_at__isnull=True
        ).update(consumed_at=timezone.now())
        challenge = OwnershipChallenge.objects.create(
            user=user,
            platform=platform,
            handle=handle,
            token_digest=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=30),
        )
    return challenge, token


def verify_challenge(user, challenge_id):
    challenge = OwnershipChallenge.objects.get(
        pk=challenge_id, user=user, consumed_at__isnull=True, expires_at__gt=timezone.now()
    )
    profile = get_adapter(challenge.platform).fetch_public_profile(challenge.handle)
    candidates = re.findall(r"n2ncp-[a-f0-9]{20}", profile)
    if not any(
        secrets.compare_digest(hashlib.sha256(t.encode()).hexdigest(), challenge.token_digest)
        for t in candidates
    ):
        raise ValidationError(
            "Token not found in the public profile. Check the field and try again."
        )
    try:
        with transaction.atomic():
            challenge = OwnershipChallenge.objects.select_for_update().get(
                pk=challenge.pk, consumed_at__isnull=True, expires_at__gt=timezone.now()
            )
            account, _ = LinkedAccount.objects.update_or_create(
                user=user,
                platform=challenge.platform,
                defaults={
                    "handle": challenge.handle,
                    "verified_at": timezone.now(),
                    "sync_cursor": {},
                    "last_synced_at": None,
                },
            )
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=["consumed_at"])
            return account
    except IntegrityError as exc:
        raise ValidationError("This handle is already linked to another account.") from exc
