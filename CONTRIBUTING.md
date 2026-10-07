# Contributing to n2ncp

Use the existing checkout; each cloud task is already isolated. Do not create a worktree unless the user explicitly requests one.

1. Read the README, architecture notes, and adapter capability boundaries.
2. Set up the Docker development stack. Work on a focused branch and keep secrets out of Git.
3. Add migrations for model changes. Preserve existing notes, problem identities, verified ownership, and delivery history.
4. Add meaningful tests for changed behavior. Run `ruff check .`, `ruff format --check .`, `pytest`, `npm run check`, `npm run build`, and `python manage.py makemigrations --check --dry-run`. Run tests against PostgreSQL before changing locking or database constraints.
5. Describe the user-visible behavior, the reason for the change, and the validation performed in your pull request.

## Adding problems and lessons

Edit `data/problems.json` using a stable platform problem ID, original title, canonical HTTPS URL, difficulty 1–5, and topic slugs. Review the statement manually for suitability. Do not copy copyrighted problem statements/editorials. Add practice explanations and implementation exercises in `data/curriculum.json` using your own words and code. Prerequisites must be acyclic and every topic should map to a useful module. Run `python manage.py seed` twice to verify repeatability.

LeetCode is strictly static: do not add API access, account linking, metadata fetching, or scraping, even for seed validation. Refer to the adapter guide before adding other platforms.

## Quality and security

Prefer accessible server-rendered behavior with progressive enhancement. Keep dependencies pinned and review updates. Do not add remote scripts, raw HTML rendering of notes, unbounded network requests, external password collection, or automatic retries after an ambiguous SMTP acceptance. Keep test fixtures small and free of personal data/secrets.

Report security concerns privately to the repository maintainer rather than posting exploitable details in a public issue. Never attach real credentials or production database dumps.
