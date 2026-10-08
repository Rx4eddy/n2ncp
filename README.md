# n2ncp

**Practice with purpose.** An open-source competitive programming workspace with a contest calendar, email reminders, a problem journal, and an adaptive, pattern-based practice path.

Built with Django 5.2, PostgreSQL, Redis, Celery, HTMX, Tailwind CSS, and Chart.js. MIT licensed.

## What is included

- Weekly calendar for Codeforces, AtCoder, and CodeChef, with platform filters and IANA timezone support.
- Opt-in reminders at the user’s chosen morning hour and two hours before a contest.
- Email registration, verification, login/logout, password reset, password changes, and email management.
- Public-token ownership verification and accepted-submission imports for Codeforces and AtCoder.
- Manual problem logging, personal notes, platform/topic counts, solve streaks, and an accessible 26-week activity heatmap.
- **267 static curated problems** across Codeforces, AtCoder, CSES, CodeChef, and LeetCode, extensible in `data/problems.json`.
- **32 practice modules / 206 exercises**, starting with C++ STL and progressing through two pointers, sliding windows, strings, range structures, all major DP families, graph traversal, SCCs, bridges, articulation points, matching, and flow.
- Recommendations that explain their ranking: prerequisites, experience, independent solves, recent difficulties, difficulty progression, variety, and spaced reviews.
- Docker development and production stacks; production HTTPS through Caddy.

### Platform capability boundaries

| Platform | Contest calendar | Verified linking | Accepted-solve import |
|---|---|---|---|
| Codeforces | Public API | Token in public first/last name | Public API, paginated |
| AtCoder | Public upcoming-contests page | Token in public Affiliation | Community AtCoder Problems API |
| CodeChef | Public contest endpoint | Not enabled | Manual journal only |
| CSES | No scheduled contest feed | Not enabled | Manual journal only |
| LeetCode | **None** | **None** | **None: static links and manual records only** |

CodeChef/CSES linking is deliberately disabled until a reliable public writable profile field and a supported reader are established. The adapters declare these capabilities; a handle is never treated as verified just because someone entered it. Public upstream endpoints may change, rate-limit, or block automated access. Calendar pages show synchronization status and preserve the last known schedule during outages. The app does not infer cancellation from a missing feed entry; operators can mark a confirmed cancellation in the admin.

**LeetCode is never fetched.** No adapter, API client, metadata fetch, scraper, or linking route exists for it. Seed imports are offline.

## Windows: start the website

With Docker Desktop running in Linux-container mode, download/clone this repository and double-click **`start-windows.cmd`**. It creates local settings, builds and starts the app, checks the web/email services, and opens your browser. No manual secret editing, Python, or Node installation is required for a new local setup.

Create an account on port 8000, then open its verification email in the local inbox on port 8025. Emails stay on your computer. Double-click `stop-windows.cmd` to stop without losing data. See **[the Windows guide](docs/WINDOWS.md)** for ZIP extraction, troubleshooting, and existing-installation recovery.

## Quick start: Docker

Requirements: Docker Engine with Compose v2, Git, and approximately 2 CPU cores / 4 GB RAM for a comfortable small deployment.

```bash
git clone https://github.com/Rx4eddy/n2ncp.git
cd n2ncp
cp .env.example .env
# Set SECRET_KEY and POSTGRES_PASSWORD to separately generated values:
openssl rand -hex 32
openssl rand -hex 24
# Edit .env. Keep the database password hexadecimal to avoid URL escaping issues.
docker compose up -d --build
```

The `assets` service builds the frontend; `init` migrates and seeds the database before web/worker/beat start. Development services bind only to loopback. Visit port **8000** for the application and **8025** for Mailpit in your own local environment. Register, open the verification email in Mailpit, and confirm your address. SMTP delivery runs through the worker; allow up to 30 seconds for outbox dispatch.

```bash
docker compose ps
docker compose logs --tail=100 web worker beat
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell -c \
  'from apps.contests.tasks import sync_all_contests; sync_all_contests.delay()'
docker compose exec web python manage.py seed
```

The initial calendar is intentionally empty until external synchronization succeeds. No demo contests, fake user progress, or default passwords are installed.

On Linux, set `LOCAL_UID` and `LOCAL_GID` in `.env` to `id -u` and `id -g` if they differ from 1000. Development containers use those IDs to read/write the bind-mounted checkout; production uses the fixed non-root application user.

Code changes reload in the development web process. Rebuild CSS/JS with `docker compose run --rm assets`. Restart the worker after changing task code. `docker compose down` preserves data volumes; **`down -v` deletes them**.

## Running tests

```bash
docker compose exec web ruff check .
docker compose exec web ruff format --check .
docker compose exec web pytest
# Exercise PostgreSQL constraints and concurrent delivery locking:
docker compose exec web sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest'
docker compose run --rm assets npm run check
```

Tests use isolated test databases and fixture-based upstream responses. No live platform account or SMTP credential is needed. See [validation notes](docs/VALIDATION.md) for checks actually executed during development.

### Host Python development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
npm ci
npm run build
# Inject .env values with your preferred environment manager, or export these
# development values explicitly. Django does not automatically source .env.
export DEBUG=1 SECRET_KEY="$(openssl rand -hex 32)"
export REDIS_URL=redis://127.0.0.1:6379/0
python manage.py migrate
python manage.py seed
python manage.py runserver
```

Without `DATABASE_URL`, DEBUG mode uses SQLite for lightweight development. **Use PostgreSQL for the full worker workflow**, especially concurrent delivery locking. The Docker workflow supplies PostgreSQL, Redis, and SMTP automatically. A host web process additionally needs a reachable Redis service, and running reminders needs `celery -A config worker` plus exactly one `celery -A config beat`. Do not use the in-memory test cache in production.

## How recommendations work

This is a transparent rules-based engine, not a claim of machine-learned ability estimation:

1. Exclude solved problems from new recommendations. Keep revision in a separate queue.
2. Restrict the default path to topics whose module prerequisites are complete. An explicit topic selection allows exploration ahead.
3. Start from the selected experience level. Every three independently solved problems in a pattern increase the difficulty target, capped at 5.
4. Consider the latest attempt per problem, so repeated clicks do not inflate topic mastery.
5. Prioritize suitable difficulty and patterns where the learner needed help. Diversify platforms among similarly scored candidates.
6. Schedule reviews at 1, 3, 7, 14, 30, or 60 days according to the recorded outcome and review stage.

Imported accepted submissions establish completion only. They do not establish independent mastery. Attempts are self-reported; there is no code execution/judging service. A local implementation exercise is completed by running C++ code locally (for example, `g++ -std=c++20 -O2 -Wall -Wextra solution.cpp -o solution` followed by `./solution`); external problems are judged by their respective platform.

A module is complete after at least 60% of its exercises. Prerequisites guide recommendations; they do not lock users out of lessons. Difficulty 1–5 is an editorial scale, not an exact conversion between platform ratings. Pattern hints for external exercises are explicitly distinguished from problem-specific editorials.

## Architecture

```text
Browser ── Caddy (HTTPS) ── Gunicorn / Django ── PostgreSQL
                                │                    ▲
                                └── Redis ── Celery workers ── SMTP
                                      ▲              │
                                  Celery Beat        └── fixed public platform hosts
```

- `apps/accounts`: custom email-based user, secure authentication, profile, timezone, preferences.
- `apps/platforms`: capability-declaring adapters, expiring ownership challenges, isolated account imports.
- `apps/contests`: normalized contest records and refresh tasks.
- `apps/journal`: canonical problem identities, notes, local-day analytics.
- `apps/practice`: prerequisites, lessons, exercises, attempts, completion, review intervals.
- `apps/recommendations`: problem bank, topic tags, explainable ranking, idempotent seed command.
- `apps/notifications`: reminder planning, database outbox, SMTP delivery, scoped unsubscribe links.
- `templates`, `frontend`: server-rendered accessible pages, compiled styles, self-hosted JavaScript.

The PostgreSQL outbox is the durable source of pending email work. Beat scans it every 30 seconds; publishing a task to Redis is not the sole record of delivery intent. Unique constraints prevent duplicate reminders, and row locking allows only one worker to claim a pending message. Before sending, the worker rechecks consent, address verification, contest cancellation, timezone, and start time.

Morning reminders after the contest start are omitted. An early-morning contest’s two-hour reminder may fall on the previous local date. Reminders over 30 minutes late are skipped. DST calculations use IANA timezones; ambiguous morning hours select the earlier occurrence and nonexistent hours advance through the gap.

SMTP cannot guarantee exactly-once delivery when a connection fails after the server may have accepted a message. Explicit rejections receive bounded retries. Ambiguous errors and interrupted deliveries become `uncertain` for operator inspection, preventing blind duplicate sends. See [operations](docs/DEPLOYMENT.md#email-and-job-operations).

## Security

Argon2 password hashes, verified email login, secure HTTP-only sessions, CSRF protection, escaped plain-text notes, restrictive CSP, server-side validation, authentication and action rate limits, bounded HTTP responses, fixed upstream hosts, and non-root application containers are included. Redirect-following is disabled for upstream requests. External handle paths are encoded and validated. Manual problem URLs are parsed but never fetched.

Only Caddy is publicly exposed in production. Django trusts its forwarding headers; do not publish the Gunicorn port or insert untrusted proxies without updating this policy. Authentication rate limits use Redis and Caddy’s overwritten real-client-IP header. Keep secrets in `.env`/your secret manager, not Git. The production access log omits URLs to avoid recording reset/unsubscribe tokens.

For deployment, operations, backups, and upgrades, follow **[the VPS deployment guide](docs/DEPLOYMENT.md)**. For adapter development, see **[ADAPTERS.md](docs/ADAPTERS.md)**. Contributions are welcome: **[CONTRIBUTING.md](CONTRIBUTING.md)**.
