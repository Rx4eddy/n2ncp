# Deploy n2ncp on an Ubuntu/Debian VPS

This guide builds and runs the application on a single Linux VPS using Docker Compose, PostgreSQL, Redis, Celery, and Caddy. It does not deploy anything by itself. Start with 2 vCPU, 4 GB RAM, and enough disk for database growth/backups. Adjust workers after measuring traffic.

## 1. Prepare the host

Install Docker Engine and the Compose plugin using the signed repositories in Docker's official distribution instructions:

- https://docs.docker.com/engine/install/ubuntu/
- https://docs.docker.com/engine/install/debian/

Do not disable package signature verification. Validate with:

```bash
docker version
docker compose version
sudo apt-get update
sudo apt-get install -y git curl openssl
```

Use a dedicated deployment user with appropriate Docker access. Membership in the Docker group grants root-equivalent privileges. Enable your cloud firewall for SSH from your administration addresses and public TCP ports 80/443. UDP 443 is optional for HTTP/3. Leave PostgreSQL, Redis, and Gunicorn unexposed. Docker-published ports have their own firewall behavior; this stack publishes only Caddy in production.

## 2. Configure DNS

Point the chosen hostname's A record to the VPS. Set AAAA only if IPv6 reaches the same server. Caddy must be reachable on 80 and 443 for ACME validation and renewal. A real domain and working public DNS are required to validate Let's Encrypt issuance; localhost tests cannot establish that.

## 3. Fetch the application and set secrets

```bash
git clone https://github.com/Rx4eddy/n2ncp.git
cd n2ncp
cp .env.example .env
chmod 600 .env
openssl rand -hex 32  # use output as SECRET_KEY
openssl rand -hex 24  # use separate output as POSTGRES_PASSWORD
```

Edit `.env` securely. Set:

| Variable | Production value |
|---|---|
| `SECRET_KEY` | A unique long random secret; keep stable across restarts |
| `DEBUG` | `0` |
| `DOMAIN` | Your hostname, e.g. `cp.yourdomain.tld` |
| `ALLOWED_HOSTS` | The same hostname; no scheme |
| `SITE_URL` | `https://` plus the hostname |
| `ACME_EMAIL` | Certificate contact email |
| `POSTGRES_DB`, `POSTGRES_USER` | Database/user names; defaults are `n2ncp` |
| `POSTGRES_PASSWORD` | Separate random hex password |
| `DATABASE_URL` | Used for host execution; Compose constructs its own URL from the PostgreSQL fields |
| `REDIS_URL` | Compose supplies the internal Redis URL |
| `EMAIL_HOST`, `EMAIL_PORT` | Your SMTP provider, usually port 587 |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials from your provider |
| `EMAIL_USE_TLS` | `1` for STARTTLS on 587 |
| `EMAIL_USE_SSL` | `1` for implicit TLS on 465; never enable both TLS flags |
| `DEFAULT_FROM_EMAIL` | A sender verified with your mail provider |
| `WEB_WORKERS` | Start with `2` |

Set SPF, DKIM, and DMARC as instructed by your SMTP provider. Confirm the VPS allows outbound SMTP; some providers block it until approved. HTTP network proxies generally do not substitute SMTP passwords: SMTP credentials must be actual runtime values from your secret store. Do not paste credentials into chat or commit them.

Outbound access is needed to your SMTP provider, container/package registries during builds, `codeforces.com`, `atcoder.jp`, `www.codechef.com`, and `kenkoooo.com`. Static CSES/LeetCode links do not require server-side egress.

## 4. Build, migrate, seed, and start

```bash
bash docker/deploy.sh
# Or run its principal operation yourself:
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 init web worker beat caddy
```

`init` runs migrations and the idempotent seed command before application processes start. Production processes use the same built image, run as UID 10001, drop capabilities, and use a read-only root filesystem. Database, Redis, Beat schedule, and Caddy state use named volumes. Only one Beat service may run; do not scale it horizontally.

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py check --deploy
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c \
  'from apps.contests.tasks import sync_all_contests; sync_all_contests.delay()'
```

Caddy automatically redirects HTTP to HTTPS and requests/renews certificates. Keep its `/data` volume. Do not use certificate-verification bypasses to make a broken deployment appear healthy.

`check --deploy` may report `security.W021` because HSTS preload is intentionally disabled. Enable preload only after the domain owner has reviewed the browser preload requirements; do not suppress or blindly satisfy this advisory.

## 5. Verify the actual deployment

```bash
curl --fail --show-error https://YOUR_DOMAIN/health/
curl --head http://YOUR_DOMAIN/
```

Expect `{"status":"ok"}` from the health endpoint and an HTTPS redirect from HTTP. Register a real test account, receive and confirm the verification email, log a problem, record a practice attempt, and inspect the updated dashboard. Opt into reminders and verify worker/outbox status. Check each upstream synchronization independently; one successful platform does not validate the others.

`/health/` checks PostgreSQL and Redis. It does not prove SMTP deliverability, healthy upstream platforms, or a running scheduler. Monitor the worker container health, Beat logs, `SyncRun` records, pending-email age, and failed/uncertain outbox counts in the Django admin. Restrict admin access at your ingress if needed and use a strong unique administrator password.

## Email and job operations

Reminder planning runs every five minutes; outbox dispatch runs every 30 seconds. Redis queue loss is recoverable for still-pending messages because PostgreSQL retains delivery intent. Do not flush Redis casually; authentication rate limits and task locks also live there.

An ambiguous SMTP outcome is quarantined as `uncertain`; it is not silently retried. Inspect the SMTP provider’s logs using the message ID `n2ncp-outbox-ID@n2ncp.local`. If the provider confirms that the message was **not** delivered:

```bash
docker compose -f docker-compose.prod.yml exec web \
  python manage.py retry_email MESSAGE_ID --confirmed-not-delivered
```

Successful transactional email bodies are redacted to avoid retaining verification/reset tokens. Treat the database and backups as private because they contain email addresses, notes, and pending message bodies. Plan a retention policy for your deployment. A stopped service can leave an in-flight message uncertain after five minutes; investigate before retrying.

## Backups and restoration

Store encrypted backups off the VPS, with restricted access and a tested retention policy. This command captures PostgreSQL in a portable custom format:

```bash
mkdir -p backups
chmod 700 backups
backup_file="backups/n2ncp-$(date -u +%Y%m%dT%H%M%SZ).dump"
(umask 077; docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_file")
# Verify the archive is readable:
docker compose -f docker-compose.prod.yml exec -T db pg_restore --list < "$backup_file"
```

Restore into a **separate empty recovery database** first, never over your only live copy. With the recovery database already created, substitute its name below:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d n2ncp_recovery' < "$backup_file"
```

Run migrations/checks against the recovery database and verify representative accounts, notes, and problem counts before using it. Back up `.env` through your secure secret-management process. Preserve Caddy certificate data and record image/release versions. Never run `docker compose down -v` during an upgrade.

## Upgrades and rollback

1. Back up and test the backup. Read the release’s migration notes.
2. Fetch the intended reviewed commit/tag. Avoid deploying unreviewed branch tips automatically.
3. Build an explicitly tagged image with `IMAGE_TAG=<release>` and retain the previous image.
4. Run the deployment script and check migration output, service health, login, queues, and a functional request.
5. If needed, roll back to the previous image only when its code supports the current schema. Otherwise restore the pre-upgrade database into a recovery database and switch during a controlled maintenance window. Account for any writes since the backup.

Do not assume every migration is reversible or that image rollback reverses database changes. This project ships CI checks and a deployment guide, not unattended production deployment credentials.

## Cloud development caveats

Some managed cloud environments require an egress proxy and a custom trusted CA for package downloads, and their nested Docker bridge may not have normal external DNS. Use the platform-supported proxy and CA trust mechanisms without disabling TLS verification. Keep any environment-specific Compose override outside the checkout; it must not replace the VPS production networking configuration. Saving cloud setup drafts does not deploy the application or issue a TLS certificate.
