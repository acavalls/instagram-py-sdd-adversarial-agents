# Cycle 6 audit findings — carried forward

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented. Cycle 6
(2026-11-08-06-regularize-audit-drift) regularized the accumulated drift of
cycles 1-5: ALL 19 carried findings with an uncontroversial resolution were
resolved (by declaration or fix) and re-verified in sync by this audit —
F-01, F-02, F-03, F-04, F-05/F-07, F-06, F-08 (cycle 5), F-09, F-10,
N-01 (cycle 3), N-02, N-03 (cycle 3), N-04, N-05, N-06, S-01, S-02, W-1,
C4-01, C4-02, C5-01, C5-02. W-2 remains a declared out-of-scope process
escalation. Five new low findings were detected this cycle; none contradicts
a declared scenario.

| ID    | Type        | Severity | Summary                                                                                                                                   | Recommendation |
| ----- | ----------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| C6-01 | SPEC→CODE   | low      | The API login endpoint trims surrounding whitespace from the submitted username (LoginSerializer.username lacks trim_whitespace=False), so a padded username authenticates; registration paths reject padded usernames, so no storage path can hold one — behaviorally inert leniency, undeclared | Declare the login-side trimming leniency, or add trim_whitespace=False to LoginSerializer.username for symmetry |
| C6-02 | SPEC→CODE   | low      | API registration trims surrounding whitespace from the email (DRF EmailField default) while the web path rejects padded emails; storage and uniqueness stay byte-exact after the trim; asymmetry undeclared | Declare the API email-trim pattern (mirroring the caption-trim precedent), or align the paths |
| C6-03 | TESTS       | low      | Six pre-cycle-6 scenario titles are covered only by sibling-named tests (posts feed/scroll, web-ui profile link and auth layout, social follow-failure); cycle-6 scenarios all have scenario-named tests; the config traceability rule holds in spirit, not literally, for those six | Rename the six tests (or add thin scenario-named aliases) |
| C6-04 | SPEC→CODE   | low (in doubt) | DRF defaults include SessionAuthentication before JWT, so API endpoints also accept session-cookie auth (this is what keeps /docs/ usable without a token); config principle says sessions are web-only; no scenario declares the session fallback | Business decision: declare the session fallback in config/specs or restrict API auth to JWT |
| C6-05 | ENVIRONMENT | low      | The cycle-6 config rewording ("gradients ... not a shipped requirement") is partially false: the shipped stylesheet contains one decorative story-ring linear-gradient (style.css:874); the fonts claim remains accurate | One more config wording tweak (acknowledge the shipped accent gradient), or strip the gradient |
| W-2   | PROCESS     | low      | Whether Bad's targeted inspection runs count toward the 6-run budget remains undecided (declared out of scope by cycle 6; cycle 6 itself exceeded minutes 7/6, honestly reported) | Business decision: amend the budget policy text or leave as-is |

Sandbox/verification caveats (not drift): visual rendering, real-browser
HTMX behavior, true parallelism (2 thread-race tests skip honestly on
shared-cache SQLite), JWT cryptography/real elapsed-time expiry, production
deployment, interactive Swagger UI, interactive admin flows and real
filesystem media storage remain unverified.

Project state after cycle 6: 6/6 changes implemented, verified, archived
and audited. Living specs: user-accounts 8 req/26 scen, posts 8/28, social
6/24, stories 6/17, web-ui 6/18, api-docs 1/2, admin-console 1/3. Suite:
512 passed, 2 skipped, 0 xfails, coverage 99.12%. All genuine defects
(N-05 card links, F-01 bob bootstrap, F-02 createsuperuser, F-03 bulk
passwords) closed and pinned; the two adversarial bugs (BUG-001/BUG-002,
password lookalikes) closed by provenance-based hashing. Remaining debt is
the five low findings above plus the W-2 policy question.
