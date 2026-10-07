from django import forms
from django.utils import timezone

from apps.recommendations.models import Topic

from .models import JournalEntry
from .services import canonical_problem_url


class JournalForm(forms.Form):
    url = forms.URLField(max_length=500, label="Problem URL", assume_scheme="https")
    title = forms.CharField(max_length=300)
    solved_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    topics = forms.ModelMultipleChoiceField(queryset=Topic.objects.all(), required=False)
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=False, max_length=10000
    )
    independent = forms.BooleanField(required=False, label="Solved independently")

    def clean_url(self):
        url = self.cleaned_data["url"]
        try:
            self.identity = canonical_problem_url(url)
        except ValueError as exc:
            raise forms.ValidationError("Invalid URL") from exc
        return url

    def clean_solved_at(self):
        value = self.cleaned_data["solved_at"]
        if value > timezone.now():
            raise forms.ValidationError("Solve date cannot be in the future.")
        return value


class NotesForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}
