from zoneinfo import available_timezones

from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    timezone = forms.ChoiceField(choices=[(z, z) for z in sorted(available_timezones())])
    morning_hour = forms.IntegerField(min_value=0, max_value=23)
    daily_goal = forms.IntegerField(min_value=1, max_value=20)

    class Meta:
        model = User
        fields = ["first_name", "timezone", "morning_hour", "experience", "daily_goal"]
