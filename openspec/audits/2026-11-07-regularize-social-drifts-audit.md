# Spec Audit — 2026-11-07 (post regularize-social-drifts archive)

Verdict: LIGHT DRIFT (all findings low severity; the previous F-01..F-12 set
is fully resolved — see the resolution table below). Cycle closed with the
new findings documented here for a future regularization cycle. Full report
in the cycle conversation; summary below.

## Resolution of the previous audit's findings (F-01..F-12)

All 12 resolved: F-01 first-media card wording, F-02 ordering tiebreaker,
F-03 media cap on every storage path, F-04 bulk username rule, F-05 follow
race translation, F-06 literal search (Django 6 ORM already escapes LIKE
wildcards; original finding factually wrong), F-07 profile-grid wording,
F-08 config Django 6+, F-09 unowned pinned behaviors now spec-owned,
F-10 create_user(None) fixed (zero xfails remain), F-11/F-12 admin and seed
accepted as dev tooling by recorded decision.

## New findings and recommended resolutions (none applied)

| ID | Type | Finding | Recommendation |
|----|------|---------|----------------|
| N-01 | CODE→SPEC | `PostQuerySet.update()` with an over-limit caption silently returns 0 (no validation error); the invariant holds but the scenario's THEN wording is unmet on that branch | (a) posts delta owning the bulk-path silent-refusal contract (mirroring how user-accounts owns its bulk rule), or make the guard raise |
| N-02 | SPEC→CODE | Legal bulk updates on guarded fields are impossible (bulk_update no-op; username bulk_update raises) — OBS-R3-1/2/3 accepted-open | (b) fix at the `bulk_update` level in a future change (never by loosening `update()`) |
| N-03 | CODE→SPEC | Non-literal (F()/Combinable) username writes are refused with USERNAME_LENGTH_ERROR even when the resolved value would be legal — beyond what the scenario mandates | (a) delta owning the non-literal-refusal contract and its error shape |
| N-04 | TESTS | `test_atk_r026` passes vacuously under the total no-op; per-target application is not pinned | (b) fix the test together with N-02 |
| N-05 | SPEC→CODE | API list responses expose `first_image_url` (first image, not first media file) — unowned response field | (a) one-line delta owning the field (first-image API thumbnail vs first-media card) |

## Coverage at close

- posts: 19 scenarios, user-accounts: 25, social: 16, api-docs: 2 — all with
  a traceable test.
- Gates: pytest 404 passed / 0 failed, coverage 99.52-99.53%, ruff 0 issues,
  mypy 0 errors, makemigrations --check clean.

## Not verified

Browser-level HTMX rendering (live probes), Django admin interactions (out
of spec contract by decision), production settings execution, live
seed_demo_data run against the reference app, true multi-process concurrency
beyond the DB-constraint level.
