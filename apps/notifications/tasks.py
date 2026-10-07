import smtplib
from datetime import timedelta

from allauth.account.models import EmailAddress
from celery import shared_task
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from apps.contests.models import Contest

from .models import EmailOutbox, ReminderDelivery, ReminderPreference
from .services import reminder_times, render_reminder


@shared_task
def plan_reminders():
    now = timezone.now()
    verified = EmailAddress.objects.filter(verified=True, primary=True).values("user_id")
    preferences = ReminderPreference.objects.filter(
        enabled=True, user__is_active=True, user_id__in=verified
    ).select_related("user")
    for pref in preferences.iterator():
        for contest in Contest.objects.filter(
            platform=pref.platform,
            cancelled=False,
            start_at__gt=now,
            start_at__lte=now + timedelta(days=2),
        ):
            for kind, due in reminder_times(pref.user, contest).items():
                # Do not send old reminders after a long outage or a new opt-in.
                if due < now - timedelta(minutes=30):
                    continue
                with transaction.atomic():
                    reminder, _ = ReminderDelivery.objects.update_or_create(
                        user=pref.user, contest=contest, kind=kind, defaults={"due_at": due}
                    )
                    subject, body, headers = render_reminder(reminder)
                    outbox, created = EmailOutbox.objects.get_or_create(
                        reminder=reminder,
                        defaults={
                            "recipient": pref.user.email,
                            "subject": subject,
                            "body": body,
                            "headers": headers,
                            "available_at": due,
                        },
                    )
                    if not created and outbox.status == "pending":
                        outbox.available_at, outbox.subject, outbox.body = due, subject, body
                        outbox.save(update_fields=["available_at", "subject", "body"])


@shared_task
def dispatch_outbox():
    now = timezone.now()
    # A worker dying during SMTP might already have delivered the message.
    # Quarantine that delivery for operator review instead of sending blindly.
    EmailOutbox.objects.filter(status="sending", claimed_at__lt=now - timedelta(minutes=5)).update(
        status="uncertain",
        last_error="Worker interrupted during delivery; inspect SMTP logs before retrying",
    )
    for pk in EmailOutbox.objects.filter(status="pending", available_at__lte=now).values_list(
        "pk", flat=True
    )[:200]:
        deliver_email.delay(pk)


@shared_task
def deliver_email(outbox_id):
    now = timezone.now()
    with transaction.atomic():
        item = (
            EmailOutbox.objects.select_for_update()
            .filter(pk=outbox_id, status="pending", available_at__lte=now)
            .first()
        )
        if not item:
            return
        if item.reminder_id:
            reminder = item.reminder
            if (
                not ReminderPreference.objects.filter(
                    user=reminder.user, platform=reminder.contest.platform, enabled=True
                ).exists()
                or not reminder.user.is_active
                or not EmailAddress.objects.filter(
                    user=reminder.user, email=reminder.user.email, verified=True
                ).exists()
            ):
                item.status = "cancelled"
            else:
                due = reminder_times(reminder.user, reminder.contest).get(reminder.kind)
                if (
                    reminder.contest.cancelled
                    or due is None
                    or reminder.contest.start_at <= now
                    or due < now - timedelta(minutes=30)
                ):
                    item.status = "cancelled"
                elif due > now:
                    item.available_at = due
                    item.save(update_fields=["available_at"])
                    return
                else:
                    item.recipient = reminder.user.email
                    item.subject, item.body, item.headers = render_reminder(reminder)
        if item.status == "cancelled":
            item.save(update_fields=["status"])
            return
        item.status = "sending"
        item.claimed_at = now
        item.attempts += 1
        item.save()
    try:
        EmailMessage(
            item.subject,
            item.body,
            to=[item.recipient],
            headers={**item.headers, "Message-ID": f"<n2ncp-outbox-{item.pk}@n2ncp.local>"},
        ).send(fail_silently=False)
    except (
        smtplib.SMTPConnectError,
        smtplib.SMTPRecipientsRefused,
        smtplib.SMTPSenderRefused,
        smtplib.SMTPDataError,
        ConnectionRefusedError,
    ) as exc:
        # These failures explicitly precede acceptance or reject the message.
        item.status = "pending" if item.attempts < 5 else "failed"
        item.available_at = timezone.now() + timedelta(seconds=min(3600, 60 * 2**item.attempts))
        item.last_error = type(exc).__name__
    except Exception as exc:
        item.status = "uncertain"
        item.last_error = f"{type(exc).__name__}: delivery outcome unknown; inspect SMTP logs"
    else:
        item.status = "sent"
        item.sent_at = timezone.now()
        # Avoid retaining password reset/verification tokens in delivery history.
        if not item.reminder_id:
            item.body = "[Delivered transactional email; body redacted]"
    item.save()
