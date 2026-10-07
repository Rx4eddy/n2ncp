#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  echo 'Create and securely configure .env from .env.example first.' >&2
  exit 1
fi
# Read values for validation only. Never source an arbitrary .env as shell code.
python3 - <<'PY'
from pathlib import Path
values={}
for line in Path('.env').read_text().splitlines():
    if line and not line.lstrip().startswith('#') and '=' in line:
        key,value=line.split('=',1)
        values[key.strip()]=value.strip().strip('"').strip("'")
required=['SECRET_KEY','POSTGRES_PASSWORD','DOMAIN','ACME_EMAIL','ALLOWED_HOSTS','SITE_URL','EMAIL_HOST','DEFAULT_FROM_EMAIL']
missing=[k for k in required if not values.get(k) or 'replace-with' in values[k] or 'example.com' in values[k]]
if missing:
    raise SystemExit('Configure these .env keys: '+', '.join(missing))
if values.get('DEBUG')!='0' or values['SITE_URL']!='https://'+values['DOMAIN']:
    raise SystemExit('Set DEBUG=0 and SITE_URL=https://DOMAIN')
if values['DOMAIN'] not in values['ALLOWED_HOSTS'].split(','):
    raise SystemExit('DOMAIN must be in ALLOWED_HOSTS')
if values['EMAIL_HOST']=='mailpit':
    raise SystemExit('Set a real production SMTP host')
if len(values['SECRET_KEY'])<50 or len(values['POSTGRES_PASSWORD'])<24:
    raise SystemExit('Generate longer SECRET_KEY and POSTGRES_PASSWORD values')
PY
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
echo 'Inspect service health and validate HTTPS, registration, and email using docs/DEPLOYMENT.md.'
