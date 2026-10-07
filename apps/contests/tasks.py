import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.platforms.adapters import CONTEST_PLATFORMS, get_adapter
from apps.platforms.adapters.base import PlatformError
from apps.platforms.models import SyncRun

from .models import Contest

logger = logging.getLogger(__name__)


@shared_task
def sync_all_contests():
    for platform in CONTEST_PLATFORMS:
        sync_contests.delay(platform)


@shared_task(bind=True, max_retries=3)
def sync_contests(self, platform):
    lock = f"contest-sync:{platform}"
    if not cache.add(lock, True, timeout=240):
        return
    retry = False
    run = SyncRun.objects.create(platform=platform, kind="contests")
    try:
        rows = get_adapter(platform).fetch_contests()
        for row in rows:
            Contest.objects.update_or_create(
                platform=platform, external_id=row.pop("external_id"), defaults=row
            )
        # Missing upstream entries are not assumed cancelled; retain last known data.
        run.success = True
        run.detail = f"Updated {len(rows)} contests"
    except Exception as exc:
        retry = isinstance(exc, PlatformError)
        run.detail = f"Sync failed: {type(exc).__name__}"
        logger.warning("Contest sync failed: %s (%s)", platform, type(exc).__name__)
    finally:
        run.finished_at = timezone.now()
        run.save()
        cache.delete(lock)

    if retry and self.request.retries < self.max_retries:
        raise self.retry(countdown=60 * 2**self.request.retries)
