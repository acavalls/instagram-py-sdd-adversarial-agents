# GBU Report — 2026-11-08-07-resolve-cycle6-findings

## Summary

Mini-regularization closing the cycle-6 audit's five low findings (C6-01..
C6-05) plus the W-2 policy question. Documentation-first: no production
code changes. Suite: 527 passed, 2 skipped, coverage 99.14% (includes Bad's 12 attack tests).

## Group results

| Group | Scope | Good | Ugly | Result |
| ----- | ----- | ---- | ---- | ------ |
| 1 | user-accounts declarations (C6-01/C6-02/C6-04): 3 scenario-named tests for the API email trim, login username trim and session-cookie fallback | 1 iter | APPROVED iter 1 | ✅ |
| 2 | C6-03 six test renames (assertions unchanged); config.yaml (gradient acknowledged, session auth declared); workflow.md budget policy (W-2) | 1 iter | APPROVED iter 1 | ✅ |
| Bad | 12 hostile attacks on the declared leniencies and renames | — | SURVIVES iter 1, 0 bugs | ✅ |

## Notable facts

- The living web-ui spec has "Login renders the auth card" and
  "Register renders the auth card" as separate scenarios; the faithful
  mapping produced one rename per scenario (audit's "six renames" holds).
- Bad verified exactly ONE shipped linear-gradient (style.css:874, story
  ring) — the config acknowledgment is accurate.
- Declared behaviors Bad confirmed inert/defended: trimmed-form email
  collision → 409; unicode whitespace (NBSP/em-space) trimmed at login;
  passwords byte-exact (not trimmed); expired/replayed sessions rejected;
  CSRF enforced on unsafe session-auth methods; session identity wins over
  a foreign JWT (documented spec-silent).

## Budget

- Good/Ugly: 1 iteration each, no fix loop needed.
- Bad: 1/6 test runs, 4/6 minutes, 1/3 iterations — within budget.

## Manual validation script

Run the dev server and verify:

1. `POST /api/auth/login/` with `"  bob  "` + correct password → 200 with
   tokens (declared trim).
2. `POST /api/auth/register/` with `"  padded@example.com  "` → 201,
   stored as `padded@example.com`; repeat → 409.
3. Log into the web UI, then open `/docs/` without any token → the
   authenticated operations work (session-cookie fallback).
4. Login with password `" bob-ig-pass-1 "` (spaces) → 401 (passwords are
   byte-exact, never trimmed).
5. POST to an API endpoint with a session cookie and no CSRF token → 403.
