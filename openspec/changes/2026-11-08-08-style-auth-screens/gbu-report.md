# GBU Report — 2026-11-08-08-style-auth-screens

## Summary

Visual-only restyle of the auth screens (login + register): brand Google
Fonts (Grand Hotel logo script + Inter body) and the brand gradient
(purple/pink/orange) on the auth background, card polish. Zero behavior
changes — all auth flows, templates structure and pinned tests untouched.
Suite: 539 passed, 2 skipped, coverage 99.16% (after the PAUSE-1 brand-naming group).

## Group results

| Group | Scope | Good | Ugly | Result |
| ----- | ----- | ---- | ---- | ------ |
| 1 | Fonts link + logo hook + auth-scoped CSS + scenario test | 1 iter | APPROVED iter 1 (a11y note: CSS wordmark has no accessible name — decorative, non-blocking) | ✅ |
| 2 | config.yaml frontend line (auth screens ship the target styling) + gates | orchestrator (docs) | — | ✅ |
| Bad | 5 attacks: CSS leak hunt, auth E2E, fonts-link uniqueness, logo DOM, test honesty | — | SURVIVES iter 1, 0 bugs | ✅ |

## Budget

- Good/Ugly: 1 iteration, no fix loop.
- Bad: **8/6 test runs, 8/6 minutes, 1/3 iterations — overruns reported
  honestly (runs 3-7 were debug iterations of Bad's own fixtures:
  underscore username vs the alphanumeric validator, wrong error string,
  missing re.DOTALL, direct-ORM user creation vs the register flow).**
  Per the amended W-2 policy every execution counts, inspections included.

## Notes

- Bad's fixture curiosity (not a bug, out of scope): a user created via
  `User.objects.create(password=make_password(...))` cannot authenticate —
  the provenance hashing design (BUG-002 fix) treats marker-less direct
  hash assignment on a new object as raw and re-hashes it. Direct hash
  assignment without the marker is declared forbidden; trusted writers
  (set_password, migration marker) are unaffected.
- Offline degradation: auth pages fall back to system fonts (declared in
  design.md).

## PAUSE-1 addition: brand naming (group 3)

Sheriff feedback folded in: the visible product name is now "Instagram"
everywhere — page titles ("· Instagram"), sidebar label, feed sidebar
footer ("© 2026 Instagram"), auth wordmark, OpenAPI title "Instagram API".
Ugly REJECTED iter 1 (footer promised on any authenticated page but only
the feed has one) -> delta rescoped honestly -> APPROVED iter 2. Bad
budget was already exhausted; the rebrand was verified via the full suite
and Ugly static greps (no stray "django_ig" outside negative assertions).

## Manual validation script

Run the dev server and verify:

1. Open `/web/login/` — brand gradient background (purple→pink→orange),
   script-font "django_ig" logo, polished card; log in with bob → feed.
2. Open `/web/register/` — same styled layout; register a user →
   redirected to login.
3. Log in with a wrong password → "Invalid credentials" on the restyled
   page.
4. Feed/profile pages look unchanged (no gradient background, system
   fonts).
5. Block `fonts.googleapis.com` (or go offline) — auth pages still
   readable with system font fallbacks.
