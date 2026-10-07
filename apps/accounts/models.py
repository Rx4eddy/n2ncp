from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationError("Choose a valid IANA timezone, such as Asia/Kolkata.") from None


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    timezone = models.CharField(max_length=64, default="UTC", validators=[validate_timezone])
    morning_hour = models.PositiveSmallIntegerField(default=8)
    experience = models.CharField(
        max_length=16,
        default="beginner",
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
    )
    daily_goal = models.PositiveSmallIntegerField(default=2)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="email_case_insensitive"),
            models.CheckConstraint(
                condition=models.Q(morning_hour__lte=23), name="valid_morning_hour"
            ),
            models.CheckConstraint(
                condition=models.Q(daily_goal__gte=1, daily_goal__lte=20), name="valid_daily_goal"
            ),
        ]
