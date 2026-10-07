import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.journal.models import JournalEntry
from apps.recommendations.models import Problem, Topic

from .adapters import get_adapter
from .adapters.base import PlatformError
from .models import LinkedAccount, SyncRun

logger = logging.getLogger(__name__)


@shared_task
def sync_all_accounts():
    for pk in LinkedAccount.objects.values_list("pk", flat=True).iterator():
        sync_account.delay(pk)
    SyncRun.objects.filter(started_at__lt=timezone.now() - timedelta(days=30)).delete()


@shared_task(bind=True, max_retries=3)
def sync_account(self, account_id):
    lock = f"account-sync:{account_id}"
    if not cache.add(lock, True, timeout=240):
        return
    retry = False
    try:
        account = LinkedAccount.objects.filter(pk=account_id).first()
        if not account:
            return
        run = SyncRun.objects.create(platform=account.platform, kind="solves")
        try:
            solved, cursor = get_adapter(account.platform).fetch_solved_problems(
                account.handle, account.sync_cursor
            )
            expected_handle = account.handle
            with transaction.atomic():
                account = LinkedAccount.objects.select_for_update().get(pk=account_id)
                if account.handle != expected_handle:
                    return  # Handle changed while a request was in flight.
                for item in solved:
                    problem, _ = Problem.objects.get_or_create(
                        platform=item.platform,
                        problem_id=item.problem_id,
                        defaults={
                            "title": item.title,
                            "url": item.url,
                            "difficulty": item.difficulty,
                        },
                    )
                    if not problem.curated:
                        mapping = {
                            "dp": "dp",
                            "graphs": "graph-traversal",
                            "trees": "trees",
                            "binary search": "binary-search",
                            "two pointers": "two-pointers",
                            "strings": "strings",
                            "math": "math",
                            "greedy": "greedy",
                            "number theory": "number-theory",
                            "data structures": "stl",
                            "sortings": "sorting",
                            "bitmasks": "bit-manipulation",
                            "dfs and similar": "graph-traversal",
                        }
                        for tag in item.tags:
                            if tag in mapping:
                                slug = mapping[tag]
                                topic, _ = Topic.objects.get_or_create(
                                    slug=slug, defaults={"name": slug.replace("-", " ").title()}
                                )
                                problem.topics.add(topic)
                    entry, created = JournalEntry.objects.get_or_create(
                        user=account.user,
                        problem=problem,
                        defaults={
                            "solved_at": item.solved_date,
                            "verdict": item.verdict,
                            "source": "import",
                        },
                    )
                    if (
                        not created
                        and entry.source == "import"
                        and item.solved_date < entry.solved_at
                    ):
                        entry.solved_at = item.solved_date
                        entry.save(update_fields=["solved_at"])
                account.sync_cursor = cursor
                account.last_synced_at = timezone.now()
                account.status = "Synced successfully; additional history imports in batches."
                account.save()
            run.success = True
        except Exception as exc:
            retry = isinstance(exc, PlatformError)
            run.detail = f"Sync failed: {type(exc).__name__}"
            LinkedAccount.objects.filter(pk=account_id).update(status=run.detail)
            logger.warning("Platform sync failed: %s (%s)", account.platform, type(exc).__name__)
        finally:
            run.finished_at = timezone.now()
            run.save()
    finally:
        cache.delete(lock)

    if retry and self.request.retries < self.max_retries:
        raise self.retry(countdown=60 * 2**self.request.retries)
