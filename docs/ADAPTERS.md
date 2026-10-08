# Developing a platform adapter

1. Confirm the platform permits the required public access. Identify an official API or a stable public page. Do not bypass logins, bot challenges, or access controls.
2. Subclass `Adapter` in `apps/platforms/adapters/`. Declare `key`, exact `allowed_hosts`, supported capabilities, the public verification field, and any limitations.
3. Implement only supported methods. `fetch_contests()` returns external ID, title, HTTPS URL, aware start datetime, and duration in seconds. `fetch_public_profile(handle)` returns only the public user-controlled field where the ownership token can appear. Do not scan unrelated comments or full-page text for a token.
4. `fetch_solved_problems(handle, cursor)` returns `(list[SolvedProblem], next_cursor)`. Each accepted solve has `problem_id, title, url, platform, solved_date, verdict, tags, difficulty`. Preserve a stable ID and timezone-aware solve date. Bound each page and make replay safe. Cursor changes and imported solves commit together.
5. Register the adapter in `ADAPTERS`. Add exact hostnames to your deployment's outbound allowlist. No external account password should ever appear in a form, database model, log, or config field.
6. Add sanitized fixtures and tests for successful responses, empty results, pagination, malformed content, timezones, rejection, timeouts, and isolated failure. Keep network tests out of CI.

The base HTTP client accepts HTTPS on fixed hosts only, does not follow redirects, has 5-second connect / 20-second read timeouts, and caps responses at 8 MB. Tasks have finite time limits and distributed locks. Transient platform failures receive up to three retries (60, 120, and 240 seconds); schema/programming failures are recorded for diagnosis and the next periodic run. Shared per-host cooldowns prevent bursts across worker processes. The scheduler refreshes contests every 30 minutes and linked accounts hourly. Codeforces imports accepted submissions in 1,000-submission batches, replaying from the head after finishing a history pass; large histories may take multiple scheduled runs. AtCoder imports use the community API’s timestamp cursor and can lag the platform.

Ownership challenges last 30 minutes and store a SHA-256 digest of a random token. Verification locks and consumes the challenge once. A case-insensitive platform/handle constraint prevents two users from claiming the same account. Regenerating a challenge invalidates earlier pending challenges for that user/platform.

Do not infer capability from a handle existing. CodeChef/CSES are capability-disabled for linking/import until an appropriate verification surface is established. They still have manually loggable curated problems. CodeChef's contest source is implemented separately from linking.

**LeetCode is a static-only platform. Never add it to ADAPTERS, a network allowlist, a scheduled task, or a URL metadata fetcher.** Add or correct its entries only in `data/problems.json`, then run the offline seed command.

Imported problems keep source tags when they can be mapped safely to the common taxonomy. Curated metadata takes precedence over upstream fields. Do not overwrite a user's notes while importing or re-seeding.
