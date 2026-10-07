from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.notifications.models import EmailOutbox


class Command(BaseCommand):
    help = "Retry an uncertain/failed email only after checking SMTP delivery logs."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)
        parser.add_argument("--confirmed-not-delivered", action="store_true")

    def handle(self, *args, **options):
        if not options["confirmed_not_delivered"]:
            raise CommandError(
                "Check SMTP logs, then pass --confirmed-not-delivered. Retrying an accepted email causes duplicates."
            )
        updated = EmailOutbox.objects.filter(
            pk=options["id"], status__in=["uncertain", "failed"]
        ).update(
            status="pending",
            available_at=timezone.now(),
            last_error="Operator confirmed non-delivery",
        )
        if not updated:
            raise CommandError("No failed or uncertain message with that ID")
        self.stdout.write("Message scheduled for retry.")
