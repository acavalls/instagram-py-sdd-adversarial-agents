# Cycle 2 audit findings — carried forward to a future cycle

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented for a future cycle. The
living specs are openspec/specs/{user-accounts,web-ui,api-docs,posts}/spec.md;
the implemented and archived change is
openspec/changes/archive/2026-11-08-02-add-posts/. Carried-forward cycle-1
findings (F-01..F-10) were re-evaluated: all still open except F-10
(partially resolved — HTMX landed with change 02; Google Fonts and gradient
CSS remain absent). New findings this cycle: N-01..N-06.

| ID  | Type        | Severity | Summary                                                                 | Recommendation |
| --- | ----------- | -------- | ----------------------------------------------------------------------- | -------------- |
| F-01 | ENVIRONMENT | medium   | config.yaml declares the accounts.0003 dev-superuser (`bob`) bootstrap migration; it does not exist yet | Business decision: implement the migration (fix) or amend config.yaml (regularize) |
| F-02 | ENVIRONMENT | medium   | `manage.py createsuperuser` crashes: UserManager lost create_user/create_superuser via from_queryset | Fix the code: restore manager factory methods |
| F-03 | SPEC→CODE  | medium   | bulk_create can persist a plain-text password (spec says hashed, never plain-text) | Fix the code (hash on bulk path) or scope the spec |
| F-04 | CODE→SPEC  | low      | Direct save() silently refuses an invalid username; contract pinned only by tests | Regularize: add a scenario declaring the save() refusal contract |
| F-05/F-07 | SPEC→CODE/TESTS | low | API trims surrounding whitespace from usernames (201, trimmed); web rejects the same input; no scenario declares either | Business decision, then regularize + align test |
| F-06 | TESTS      | low      | Email duplicate detection is case-sensitive; xfail(strict) test pins an unspecified behavior | Business decision: case-insensitive uniqueness or not |
| F-08 | SPEC→CODE  | low      | `/admin/` route mounted, not described by any living spec | Regularize: one-line note that Django admin is out of scope |
| F-09 | SPEC→CODE  | low      | Authenticated user GETting /web/login/ is redirected to the feed; unspecified | Regularize: add a scenario to "Web session login" |
| F-10 | ENVIRONMENT | low     | Google Fonts and gradient CSS declared in the fixed stack but absent (HTMX resolved in change 02) | Regularize: reword config context as target stack, or land them in a UI package |
| N-01 | CODE→SPEC  | medium   | Spec-internal contradiction: user-accounts "Authenticated landing placeholder" still mandates the placeholder empty state while posts "Post listing" declares the personal-feed interim state (package 03 MODIFIES both — resolves it) | Resolved by package 03's MODIFIED deltas; verify at the cycle-3 audit |
| N-02 | TESTS      | low      | Scenario "Media stored under the post media path" has no scenario-named test (behavior proven by 4 incidental tests) | Fix the tests: add the scenario-named test |
| N-03 | TESTS      | low      | Scenarios "User account persisted" and "Logged-in user reaches the placeholder" lack scenario-named tests (second superseded by N-01/package 03) | Fix the tests; re-map after package 03 |
| N-04 | SPEC→CODE  | low      | API rejects invalid pagination parameters with 400 "Invalid pagination parameters"; no scenario declares it | Regularize: add a scenario to posts "Post listing" |
| N-05 | SPEC→CODE  | low      | Card header username links to /web/users/<username>/ (non-existent route until package 03); unlike the sidebar placeholder it is not declared | Package 03 wires profile pages; verify at the cycle-3 audit |
| N-06 | CODE→SPEC  | low      | Inline-edit routing contract (GET 404 unknown/non-owner, non-owner POST 403, empty-response form close) pinned only by tests | Regularize: extend posts "Caption update" scenarios |

Not verified by the audit: visual rendering, real-browser HTMX behavior,
true-parallelism concurrency, JWT cryptography, production settings, admin
flows, coverage gate re-measurement.
