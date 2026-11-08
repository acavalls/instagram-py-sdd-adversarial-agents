# Cycle 7 audit findings — carried forward

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented. Cycle 7
(2026-11-08-07-resolve-cycle6-findings) resolved all six cycle-6 findings
plus W-2 by declaration/renames/docs — every one re-verified RESOLVED and in
sync by this audit (C6-01, C6-02, C6-03, C6-04, C6-05, W-2). All carried
findings from cycles 1-6 remain resolved and in sync (F-01..F-10, N-01..
N-06, S-01/S-02, W-1, C4-01/C4-02, C5-01/C5-02). Three new low findings were
detected this cycle; none contradicts a declared scenario. 136/136 living
scenarios verified against the code; 135/136 have a scenario-named test
(exception: C7-01).

| ID    | Type      | Severity | Summary                                                                                                                                          | Recommendation |
| ----- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| C7-01 | TESTS     | low      | The C6-03 rename (test_topbar_links_to_own_profile → test_profile_link_points_to_own_profile) satisfied the twin web-ui scenario but left the twin social scenario ("Topbar links to own profile", social/User profile page) without a scenario-named test — behavior still covered by the same test, only name-traceability lost | Add a thin scenario-named alias for the social scenario, or fold the twin scenario into the web-ui one |
| C7-02 | SPEC→CODE | low      | The declared session-cookie fallback scenario covers only "no JWT" clients; the session-wins-over-foreign-JWT precedence and CSRF enforcement on session-authenticated unsafe methods are pinned by Bad's attack tests but not declared | Declare the precedence + CSRF nuance (one sentence / one scenario in the session-fallback requirement) |
| C7-03 | SPEC→CODE | low      | Anonymous API requests are rejected 403 without a WWW-Authenticate challenge (SessionAuthentication first yields no challenge); no living spec declares the anonymous-failure status/header — spec-silent since cycle 1 | Declare the 403-no-challenge surface in user-accounts, or escalate if a 401 + Bearer challenge is wanted |

Note: the "createsuperuser CommandError surface" and `--noinput`
unusable-password marker were re-checked and are Django tooling semantics,
not product behavior — no finding.

Sandbox/verification caveats (not drift): visual rendering, real-browser
HTMX behavior and interactive Swagger UI/admin flows (static + test-client
only), true parallelism (2 thread-race tests skip honestly on shared-cache
SQLite), JWT cryptography and real elapsed-time expiry, production
deployment, real filesystem media storage and the rendered story-ring
gradient remain unverified.

Project state after cycle 7: 7/7 changes implemented, verified, archived
and audited. Living specs: user-accounts 8 req/28 scen, posts 8/28, social
6/24, stories 6/17, web-ui 6/18, api-docs 1/2, admin-console 1/3 (136
scenarios). Suite: 527 passed, 2 skipped, 0 xfails, coverage 99.14%. The
declared-leniency surface (API email/username trims, session-cookie
fallback) withstood 12 adversarial attacks with 0 bugs. Remaining debt: the
three low findings above.
