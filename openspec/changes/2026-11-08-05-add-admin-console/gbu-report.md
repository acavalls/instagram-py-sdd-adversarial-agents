# GBU Report — 2026-11-08-05-add-admin-console

## Result: APPLY_DONE — both groups approved, Bad SURVIVES

## Group loop (Good → Ugly)

| Group | Scope | Good iters | Ugly verdicts |
| ----- | ----- | ---------- | ------------- |
| 1 | Admin registrations (4 domain models) + guardrail scenarios | 2 | REJECTED iter 1 (DEV-001: the 'search' facet of "Staff manages domain models" had no test) → search assertions added → APPROVED iter 2 |
| 2 | Quality gates | 1 | APPROVED iter 1 (orchestrator-run) |

## Bad attack (🌵)

- Verdict: **SURVIVES** at attack iteration 1. Budget: 5/6 test-runner executions, ~4/6 minutes, 1 iteration (two early runs burned on Bad's own fixture bugs — reported honestly).
- 14 attack tests created: apps/accounts/tests/test_bad_attack_admin_console.py.
- Attacks repelled: anonymous deep-links to 12 admin pages (changelists, change, password, delete) land on the login page with zero object data; non-staff GET deep-links and POST change-form mutations (caption hijack + owner steal) → 302 login, no mutation; login POST with valid non-staff credentials → no admin session; raw password injected through the admin's hash-pointer field never stored (old hash untouched, old credential valid); admin-set password hashes and authenticates; self password rotation keeps the session; 2201-char caption refused through the admin; Story expires_at forced to 2030 through the admin refused by the 24h invariant (nothing stored); self-follow via the admin add form refused by the DB check constraint; user delete cascade behaves per domain models; admin add-user form grants no staff/superuser rights and no raw password; non-staff POST of is_staff+is_superuser onto its own change form rejected.
- Bugs found: **none**. No xfail pins.
- Minor observations (spec-silent, not bugs): a bare is_staff user without model permissions reaches the admin index with HTTP 200 (empty app list) and gets 403 on change views — spec only mandates redirects for anonymous/non-staff; staff cannot ADD a Story through the admin (required manual expires_at always mismatches created_at+24h → refused; invariant holds, probe partially confounded by a missing image field — honest caveat); user delete cascades posts/stories/follows (intended domain semantics, shown on the confirm page).
- Orchestrator actions on Bad's output: removed the temporary diagnostic probe file (apps/accounts/tests/test_bad_attack_probe_tmp.py) that Bad's sandbox policy prevented it from deleting; normalized the attack test file (ruff format). Test content otherwise untouched.

## Final gates (all green)

- pytest: **443 passed, 2 skipped, 1 xfailed** — coverage **99.11%** (≥ 80 required)
- ruff check: 0 issues · ruff format --check: 191 files clean · mypy: 0 errors (119 files) · manage.py check: no issues

## Carried findings touched by this change

- F-08 (admin route unspecified): **RESOLVED by this change** — the `/admin/` route is now specified by the admin-console capability (verify at the cycle-5 audit).

## Notes

- The staff test fixture is is_staff=True + is_superuser=True: Django's admin denies model access to staff without model permissions; the design's non-goal excludes role management beyond is_staff. Manual validation should use an equivalent superuser/staff-with-permissions account.
- Post admin omits a media-count column (would need a custom annotated queryset; the task marked it optional).

## Manual validation script (for the Sheriff)

1. Create a staff user in the shell: `.venv/bin/python manage.py shell -c "from apps.accounts.models import User; u = User(username='staffer', email='s@x.io', is_staff=True, is_superuser=True); u.set_password('staffpass-1'); u.save()"` (avoids the broken createsuperuser, finding F-02).
2. Anonymous window → `/admin/` → admin login page (no console).
3. Log in as staffer → the index lists User, Post, Story, Follow; open each changelist, search (`q=`), open a change view and edit.
4. Change a user's password through `/admin/accounts/user/<id>/password/`; confirm the user can log in with the new password from the web UI.
5. Try to reach `/admin/posts/post/` from a logged-in NON-staff session → redirected to the admin login.
