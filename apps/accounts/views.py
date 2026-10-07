from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.notifications.models import ReminderPreference
from apps.platforms.adapters import ADAPTERS, CONTEST_PLATFORMS
from apps.platforms.adapters.base import PlatformError
from apps.platforms.models import LinkedAccount, OwnershipChallenge
from apps.platforms.services import create_challenge, verify_challenge
from apps.platforms.tasks import sync_account

from .forms import ProfileForm


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        for platform in CONTEST_PLATFORMS:
            ReminderPreference.objects.update_or_create(
                user=request.user,
                platform=platform,
                defaults={"enabled": request.POST.get(platform) == "on"},
            )
        messages.success(request, "Profile and reminder preferences saved.")
        return redirect("profile")
    enabled = set(
        ReminderPreference.objects.filter(user=request.user, enabled=True).values_list(
            "platform", flat=True
        )
    )
    return render(
        request,
        "profile.html",
        {
            "form": form,
            "adapters": ADAPTERS.values(),
            "platforms": CONTEST_PLATFORMS,
            "enabled": enabled,
            "accounts": LinkedAccount.objects.filter(user=request.user),
            "challenges": OwnershipChallenge.objects.filter(
                user=request.user, consumed_at__isnull=True, expires_at__gt=timezone.now()
            ),
        },
    )


@login_required
@require_POST
@ratelimit(key="user", rate="10/h", block=True)
def link_account(request):
    try:
        challenge, token = create_challenge(
            request.user, request.POST.get("platform", ""), request.POST.get("handle", "").strip()
        )
        return render(
            request,
            "link.html",
            {"challenge": challenge, "token": token, "adapter": ADAPTERS[challenge.platform]},
        )
    except (ValidationError, PlatformError) as exc:
        messages.error(request, str(exc))
        return redirect("profile")


@login_required
@require_POST
@ratelimit(key="user", rate="15/h", block=True)
def verify_account(request, pk):
    try:
        account = verify_challenge(request.user, pk)
        sync_account.delay(account.pk)
        messages.success(request, "Ownership verified. Your first solve import is queued.")
    except (ValidationError, PlatformError, OwnershipChallenge.DoesNotExist) as exc:
        messages.error(
            request,
            str(exc)
            if not isinstance(exc, OwnershipChallenge.DoesNotExist)
            else "Challenge expired or already used. Generate a new one.",
        )
    return redirect("profile")


@login_required
@require_POST
def unlink_account(request, pk):
    get_object_or_404(LinkedAccount, pk=pk, user=request.user).delete()
    messages.success(request, "Account unlinked. Existing journal entries are retained.")
    return redirect("profile")


@login_required
@require_POST
@ratelimit(key="user", rate="4/h", block=True)
def sync_now(request, pk):
    account = get_object_or_404(LinkedAccount, pk=pk, user=request.user)
    sync_account.delay(account.pk)
    messages.success(request, "Synchronization queued.")
    return redirect("profile")
