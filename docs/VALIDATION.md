# Validation record

This record distinguishes implemented behavior from deployment checks actually run.

## Passed

- **63 automated tests against PostgreSQL 17**, including two competing workers claiming the same email; exactly one send occurs.
- Authentication email queuing, verification enforcement, CSRF, ownership tokens, expired challenges, cross-user journal protection, escaped notes, and production client-IP header handling.
- Timezone/DST reminder scheduling, idempotent planning/delivery, rescheduling, late-reminder cancellation, signed unsubscribe, explicit SMTP rejection retry, and quarantine of uncertain delivery.
- Recommendation prerequisites, difficulty progression, per-problem mastery evidence, imported-solve handling, weak-topic ranking, separate reviews, and preservation of original solve dates.
- All required pages and all 32 practice-module pages render; malformed practice targets are rejected.
- Seed repeatability, model-field validation, and an acyclic curriculum: **267 curated problems, 32 modules, 206 exercises**.
- Python lint/format checks, JavaScript syntax/build checks, migration drift checks, and static-file collection.
- npm production dependency audit: no reported vulnerabilities at validation time.
- Both Compose configurations validate. Development and production multi-stage images build with TLS verification intact.
- Full development stack starts: PostgreSQL, Redis, Mailpit, Django, Celery worker, and Beat. HTTP health checks and worker ping pass.
- End-to-end development **and production HTTPS** flows: registration -> Beat -> Redis -> worker -> SMTP/Mailpit -> verification -> login -> required pages -> journal entry -> practice progress -> static assets.
- Production application runs as UID 10001 with a read-only root filesystem. Caddy redirects HTTP to HTTPS; requests validate against its local test CA without disabling certificate verification.
- Live contest synchronization succeeds for Codeforces, AtCoder, and CodeChef. Live public accepted-submission parsing succeeds for Codeforces and AtCoder (747 and 338 accepted records respectively in the tested batches).
- PostgreSQL custom-format backup restores into a separate temporary database; restored problem/module counts are 267/32. The temporary recovery database is removed afterward.

## Scope and remaining deployment checks

The cloud host initially blocked platform requests and nested-container package downloads. Required platform domains were saved, and an environment-specific proxy/CA override outside the repository enabled validation. TLS verification was retained. Do not copy that cloud-specific proxy setup into a normal VPS deployment.

The HTTPS test uses Caddy's **local test CA**, not Let's Encrypt. Public DNS, real SMTP deliverability, and Let's Encrypt issuance/renewal must be validated on the intended VPS with its domain and mail provider. No public deployment has been performed.

`manage.py check --deploy` reports the intentional `security.W021` advisory: HSTS preload is not enabled. HSTS itself is enabled in production; browser preload enrollment should be an explicit domain-owner decision.

Ownership verification is covered with controlled profile fixtures. No real external account was claimed on behalf of a user. CodeChef/CSES linking remains capability-disabled; manual logging works. LeetCode remains entirely static and is never queried.

GitHub Actions CI is configured on pushes and pull requests. Local execution of its checks has passed; remote run status is reported separately when GitHub API access permits it. These checks are not a substitute for deployment-specific load testing, independent security review, or browser/device compatibility testing.
