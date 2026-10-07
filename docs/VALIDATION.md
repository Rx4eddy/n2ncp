# Validation record

This record distinguishes implemented behavior from deployment checks actually run.

## Verified during implementation

- Django system checks and migrations on SQLite.
- Idempotent seed import: 267 curated problems, 32 modules, 206 exercises.
- 55 automated tests, including authentication email queuing, CSRF, ownership verification, timezone/DST reminders, idempotent delivery, unsubscribe, recommendation prerequisites, review separation, journal privacy, and all required pages.
- Python lint/format checks and JavaScript syntax/build checks.
- Development and production Compose configuration validation.
- PostgreSQL, Redis, and Mailpit containers start successfully.

## Validation in progress

- Full application container startup, PostgreSQL test execution, and SMTP/worker integration.
- Production image and reverse-proxy validation.

## External prerequisites

Live contest requests from the managed cloud environment were rejected by its outbound proxy. The required domain additions have been saved to the cloud environment draft. Fixture-based adapters are tested; successful live synchronization is not claimed.

Public deployment, real SMTP deliverability, and Let's Encrypt certificate issuance require an operator-controlled domain, VPS, and SMTP configuration. No public deployment has been performed.
