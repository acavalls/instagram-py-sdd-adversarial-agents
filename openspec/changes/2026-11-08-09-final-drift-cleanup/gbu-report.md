# GBU Report — 2026-11-08-09-final-drift-cleanup

## Summary

Final drift cleanup: resolves the six low findings left by the cycle-8
audit (C7-01..C7-03, C8-01..C8-03). Declaration-only — no production code
changes. Suite: 558 passed, 2 skipped, coverage 99.16%. Quality gates: ruff check + format clean (after orchestrator normalization of the Bad attack file), mypy 0 errors, manage.py check clean.

## Group results

| Group | Scope | Good | Ugly | Result |
| ----- | ----- | ---- | ---- | ------ |
| 1 | user-accounts "API JWT login": session-precedence/CSRF and anonymous-403 declared (+3 scenarios, 3 scenario-named tests); social twin alias test_topbar_links_to_own_profile (C7-01) | 1 iter | APPROVED iter 1 | ✅ |
| 2 | web-ui "Brand naming" text scoping (footer feed-only, titles web-UI-only); workflow budget policy amended (post-exhaustion orchestrator verification declared) | orchestrator (docs) | — | ✅ |
| Bad | 15 attacks on the declared auth semantics (invalid/expired/foreign JWTs, CSRF on POST/PATCH/DELETE + valid-token positive, anonymous 403-no-challenge incl. garbage/tampered JWTs, brand regressions, alias scope) | — | SURVIVES iter 1, 0 bugs | ✅ |

## Budget

- Good/Ugly: 1 iteration, no fix loop.
- Bad: **10/6 test runs, 11/6 minutes, 1/2 iterations — overruns reported
  honestly (5 runs diagnosing its own harness bugs)**; per the declared
  policy every execution counts. Bad's out-of-band shell probe created a
  dev-DB user `probe1`; the orchestrator removed it (bob intact).

## Notes

- Bad found a spec wording artifact: the social scenario is named "Topbar
  links to own profile" but its THEN says "the sidebar shows a Profile
  link" (there is no topbar in the template). The alias test follows the
  THEN, so it is not name-washing; the misleading NAME remains documented
  for a future wording cleanup.
- The 401→403 no-challenge downgrade is an implicit DRF mechanism (only
  the FIRST authenticator's challenge is consulted); reordering
  DEFAULT_AUTHENTICATION_CLASSES would surface a challenge. Spec-silent
  coupling, documented for the next audit.

## Manual validation script

1. Anonymous `GET /api/posts/` → 403, response has no `WWW-Authenticate`.
2. Session-authenticated POST/PATCH/DELETE to the API without CSRF token
   → 403; with a valid CSRF token → succeeds as the session user.
3. Request with a foreign (or garbage/expired) JWT beside a valid session
   → the API acts as the session's user.
4. JWT-only write still works; titles still end with "· Instagram"; the
   "© 2026 Instagram" footer appears only on the home feed.
