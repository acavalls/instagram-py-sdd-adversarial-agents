# Cycle 9 audit findings — carried forward

Date: 2026-11-08. Audit verdict: LIGHT DRIFT (marginal). Cycle closed by the
Sheriff ("cerramos") with the findings below documented. Cycle 9
(2026-11-08-09-final-drift-cleanup) resolved ALL six findings left by the
cycle-8 audit — C7-01 (social scenario alias test), C7-02 (session
precedence + CSRF declared), C7-03 (anonymous 403 no-challenge declared),
C8-01 (post-exhaustion budget practice declared), C8-02 (footer scoped to
the home feed in the spec), C8-03 (titles scenario scoped to the web UI) —
and every one was re-verified RESOLVED and in sync. With this cycle, all 35
findings accumulated across cycles 1-8 are resolved. Test traceability is
complete: 143/143 living-spec scenarios have scenario-named tests. Two new
low in-doubt findings were detected; both are one-line spec-text
declarations away from literal IN SYNC.

| ID    | Type      | Severity      | Summary                                                                                                                                                       | Recommendation |
| ----- | --------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| C9-01 | CODE→SPEC | low (in doubt) | The web feed and profile windows silently clamp an invalid `page` value to page 1; the posts spec's 400 rule is pinned by its scenario only for `GET /api/posts/`, but the requirement sentence read literally could cover the web listing too | One clause in posts "Post listing" ("the web feed and profile windows treat an invalid page as page 1") or scope the 400 rule to the API |
| C9-02 | CODE→SPEC | low (in doubt) | `POST /api/auth/login/` with an unparseable JSON body answers 400 "JSON parse error" (DRF ParseError), not 401 "Invalid credentials"; the declared scenarios (wrong credentials, blank/missing fields) are all met — the doubt is whether unparseable payloads were in scope of "On any failure" | One sentence scoping "any failure" to failures of the submitted credentials/fields, or a view-level 401 guard |

Documented artifacts, verified to remain only that (no drift, no action):
- The social scenario NAME "Topbar links to own profile" whose THEN says
  "the sidebar shows a Profile link" — a spec wording artifact (no topbar
  exists in the templates); the alias test follows the THEN, so it is not
  name-washing. Rename the scenario at the next wording cleanup.
- The DRF first-authenticator challenge coupling: the declared anonymous
  403-no-challenge surface holds while SessionAuthentication stays first in
  DEFAULT_AUTHENTICATION_CLASSES; reordering would surface a 401+challenge.
  Spec-silent mechanism, documented in the archived cycle-9 gbu-report.
- Bad's cycle-8 fixture assigns make_password(...) without the
  `_password_is_hash` marker, so the storage path re-hashes the hash —
  harmless (fixture users only force_login, never authenticate by password)
  and a consequence of the declared provenance-hashing design.

Historical note (no effect): the archived cycle-9 proposal says "+2
scenarios" where the delta/report say +3 — artifact wording only.

Sandbox/verification caveats (not drift): visual rendering (CSS wordmark,
gradient, fonts — stylesheet/DOM content only), real-browser HTMX behavior,
interactive Swagger UI/admin flows, JWT cryptography and real elapsed-time
expiry, true parallelism (2 thread-race tests skip honestly on shared-cache
SQLite), production deployment (dev SECRET_KEY warning is a sandbox
artifact; production reads DJANGO_SECRET_KEY from the environment), real
filesystem media storage.

Project state after cycle 9: 9/9 changes implemented, verified, archived
and audited. Living specs: user-accounts 8 req/34 scen, posts 8/31, social
6/25, stories 6/21, web-ui 7 req/23 scen, api-docs 1/2, admin-console 1/4 —
37 requirements, 143 scenarios, 143/143 scenario-named tested. Suite: 558
passed, 2 skipped, 0 xfails, coverage 99.16%. The product is branded
"Instagram"; the auth screens ship the brand fonts and gradient. Remaining
debt: the two one-line declarations above (C9-01, C9-02).
