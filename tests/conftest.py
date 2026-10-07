import pytest
from allauth.account.models import EmailAddress
from django.core.cache import cache

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()


@pytest.fixture
def user(db):
    user = User.objects.create_user(
        "learner@example.com", "a-long-example-password", timezone="Asia/Kolkata"
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user


@pytest.fixture
def logged_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def seeded(db):
    from django.core.management import call_command

    call_command("seed", verbosity=0)
