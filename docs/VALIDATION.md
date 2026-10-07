# Validation record

This record distinguishes implemented behavior from deployment checks actually run.

## Verified during implementation

- Django system checks and migrations on SQLite.
- Idempotent seed import: 267 curated problems, 32 modules, 206 exercises.
- 62 automated tests on PostgreSQL, including a concurrent-worker row-lock test, including authentication email queuing, CSRF, ownership verification, timezone/DST reminders, idempotent delivery, unsubscribe, recommendation prerequisites, review separation, journal privacy, and all required pages.
- Python lint/format checks and JavaScript syntax/build checks.
- Development and production Compose configuration validation.
- Non-root development Docker image builds with TLS verification intact.
- Full development stack (PostgreSQL, Redis, Mailpit, Django, Celery worker, Beat) starts; HTTP health and worker ping pass.
- End-to-end registration -> Beat -> Redis -> worker -> SMTP/Mailpit -> email verification -> login -> required pages -> journal entry -> practice progress passes.
- Static CSS and JavaScript are served successfully.

## Validation in progress

- Production image and reverse-proxy validation.

## External prerequisites

Live contest requests from the managed cloud environment were rejected by its outbound proxy. The required domain additions have been saved to the cloud environment draft. Fixture-based adapters are tested; successful live synchronization is not claimed.

Public deployment, real SMTP deliverability, and Let's Encrypt certificate issuance require an operator-controlled domain, VPS, and SMTP configuration. No public deployment has been performed.
