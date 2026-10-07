from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.recommendations.models import Problem
from apps.recommendations.services import record_problem_attempt

from .forms import JournalForm, NotesForm
from .models import JournalEntry


@login_required
def journal(request):
    with timezone.override(ZoneInfo(request.user.timezone)):
        form = JournalForm(
            request.POST or None,
            initial={"solved_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")},
        )
        if request.method == "POST" and form.is_valid():
            platform, pid, url = form.identity
            with transaction.atomic():
                problem, created = Problem.objects.get_or_create(
                    platform=platform,
                    problem_id=pid,
                    defaults={"title": form.cleaned_data["title"], "url": url},
                )
                if created:
                    problem.topics.set(form.cleaned_data["topics"])
                record_problem_attempt(
                    request.user,
                    problem,
                    "independent" if form.cleaned_data["independent"] else "hinted",
                )
                JournalEntry.objects.filter(user=request.user, problem=problem).update(
                    solved_at=form.cleaned_data["solved_at"], notes=form.cleaned_data["notes"]
                )
            messages.success(
                request, "Problem logged. Your practice recommendations have been updated."
            )
            return redirect("journal")
        entries = (
            JournalEntry.objects.filter(user=request.user)
            .select_related("problem")
            .prefetch_related("problem__topics")
        )
        if request.GET.get("q"):
            entries = entries.filter(problem__title__icontains=request.GET["q"][:100])
        return render(
            request,
            "journal.html",
            {"form": form, "entries": Paginator(entries, 20).get_page(request.GET.get("page"))},
        )


@login_required
def edit_notes(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    form = NotesForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("journal")
    return render(request, "notes.html", {"entry": entry, "form": form})


@login_required
@require_POST
def delete_entry(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    entry.delete()
    messages.success(
        request, "Journal entry removed. Imported entries may return during synchronization."
    )
    return redirect("journal")
