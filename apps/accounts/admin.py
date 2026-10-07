from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class ChangeUserForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class AccountAdmin(UserAdmin):
    form = ChangeUserForm
    add_form = CreateUserForm
    ordering = ["email"]
    list_display = ["email", "is_staff", "is_active", "date_joined"]
    search_fields = ["email", "first_name"]
    fieldsets = [
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {"fields": ("first_name", "timezone", "experience", "daily_goal", "morning_hour")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    ]
    add_fieldsets = [(None, {"fields": ("email", "password1", "password2")})]
