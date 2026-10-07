# syntax=docker/dockerfile:1
FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca_bundle; fi; \
    npm ci --no-audit --no-fund
COPY frontend ./frontend
COPY templates ./templates
COPY tailwind.config.cjs ./
RUN mkdir -p static && npm run build

FROM python:3.12-slim-bookworm AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt ./
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim-bookworm AS production
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /app /var/run/celery && chown app:app /app /var/run/celery
COPY --from=dependencies /install /usr/local
WORKDIR /app
COPY --chown=app:app . .
COPY --from=assets --chown=app:app /app/static ./static
USER app
RUN DEBUG=1 SECRET_KEY=non-secret-static-build-key python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--access-logformat", "%(h)s %(m)s %(s)s %(L)s"]

FROM production AS development
COPY requirements-dev.txt ./
USER root
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip install --no-cache-dir -r requirements-dev.txt
USER app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
