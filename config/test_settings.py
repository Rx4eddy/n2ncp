import os

os.environ.setdefault("SECRET_KEY", "only-for-isolated-tests-never-deploy")
os.environ.setdefault("DEBUG", "1")
from .settings import *  # noqa: F403, E402

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
if os.getenv("TEST_DATABASE_URL"):
    from urllib.parse import urlparse

    db = urlparse(os.environ["TEST_DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db.path.lstrip("/"),
            "USER": db.username,
            "PASSWORD": db.password,
            "HOST": db.hostname,
            "PORT": db.port,
        }
    }
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
CELERY_TASK_ALWAYS_EAGER = True
SECURE_SSL_REDIRECT = False
