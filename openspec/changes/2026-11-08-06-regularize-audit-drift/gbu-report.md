# GBU Report — 2026-11-08-06-regularize-audit-drift

## Summary

Regularization of the accumulated audit drift after cycles 1–5. 14 new
scenarios declared across 6 living capabilities; code fixes: post-card
profile links (N-05), user manager tooling (F-02), bulk password hashing
(F-03), DEBUG-guarded `bob` bootstrap migration (F-01), API username
trimming removal (F-05/F-07), byte-exact emails (F-06), Profile-active
sidebar (S-01), config stack wording (F-10). Suite grew 443 → 512 passed.

## Group results

| Group | Scope | Good | Ugly | Result |
| ----- | ----- | ---- | ---- | ------ |
| 1 | Accounts (F-01–F-09) | 2 iters | REJECTED iter 1 (DEV-001 email domain normalization broke byte-exact claim; DEV-002 tasks wording) → APPROVED iter 2 | ✅ |
| 2 | Posts (N-02/N-04/N-05/N-06) | 1 iter | APPROVED iter 1 | ✅ |
| 3 | Stories (W-1/C4-01/C4-02) | 1 iter | APPROVED iter 1 | ✅ |
| 4 | Web/social/admin (C5-01/C5-02/S-01/S-02) | 1 iter | APPROVED iter 1 | ✅ |
| 5 | Config F-10 + gates | orchestrator (docs edit) | — | ✅ |
| Bad | Adversarial attack | — | 3 iterations | BUG-001, BUG-002 found and fixed; repros green |

## Bugs found by Bad (🌵) and fixed

- **BUG-001 (HIGH)**: raw passwords shaped like hash strings
  (`md5$not-a-real-md5-payload`) passed `identify_hasher` and were stored
  verbatim by bulk_create/save, never authenticating. First fix
  (identify + decode round-trip) was insufficient.
- **BUG-002 (HIGH)**: a fully decodable md5-shaped raw password
  (`md5$realsalt$<32-hex>`) passed the decode guard and was still stored
  verbatim. Definitive fix: provenance-based hashing — `_password_is_hash`
  marker set by `set_password` and by the trusted direct assignment in the
  accounts.0003 migration, plus `_original_password` load tracking
  (from_db/refresh_from_db) so stored hashes are never re-hashed. Shape
  inspection removed entirely.
- Bad repro tests: `test_bad_attack_regularization_accounts.py`,
  `test_bad_attack_regularization_web.py`,
  `test_bad_attack_reattack_decode_guard.py` — all green un-xfailed.

## Budget

- Good/Ugly: 3 fix iterations max — used 2 (group 1), 1 (groups 2–4).
- Bad: **6/6 test runs, 3/3 attack iterations, 7/6 minutes (reported
  honestly, 1 minute over)**. Budget exhausted after the BUG-002 report;
  the fix was verified by the orchestrator running Bad's repro tests
  (30/30) and the full gates (512 passed, 2 skipped, coverage 99.12%,
  ruff/mypy/check clean).

## Notable decisions implemented

- Byte-exact emails required overriding the inherited domain-case
  normalization (`User.clean`) and reworking duplicate-error mapping
  (DEV-001).
- Scenario-named tests added for every declared scenario
  (config.yaml traceability rule).

## Manual validation script

Run the dev server (`.venv/bin/python manage.py runserver`) and verify:

1. `createsuperuser` completes interactively (F-02 fixed).
2. On a fresh dev DB, `manage.py migrate` creates the superuser `bob`
   (password `bob-ig-pass-1`, staff+superuser) — log into `/admin/` as bob
   (F-01); with DEBUG off the migration must not create bob.
3. Register a padded username from the API (`POST /api/auth/register/`
   with `"  padded  "`) → 400 with the username error; same from the web
   register form (F-05/F-07).
4. Register `alice@example.com`, then `ALICE@other.com` and
   `alice@OTHER.com` → all accepted, stored byte-exactly; registering
   `alice@example.com` again → "Email already registered" (F-06).
5. Log in, open the feed: every post card's avatar/username link opens the
   owner's profile page — no 404s (N-05 fixed).
6. Profile pages highlight Profile in the sidebar; the feed highlights
   Home (S-01 fixed).
7. `GET /api/posts/?limit=0` → 400 "Invalid pagination parameters" (N-04).
8. As a non-owner, GET a post's edit form → 404 without the caption; POST
   → 403 "You can only edit your own posts" (N-06).
9. Plain (non-HTMX) POST to `/web/stories/create/` → redirect to the feed,
   story created; `POST /web/stories/not-a-uuid/view/` → 404 (W-1/C4-01).
10. `/web/profile/<uuid>/?page=2` without HTMX → full page with that
    window (C5-01); the admin index offers Groups (C5-02).
