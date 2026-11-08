# Cycle 3 audit findings — carried forward to a future cycle

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented for a future cycle. The
living specs are openspec/specs/{user-accounts,web-ui,api-docs,posts,social}/
spec.md; the implemented and archived change is
openspec/changes/archive/2026-11-08-03-add-social/. Cycle-1 findings
(F-01..F-10) and cycle-2 findings (N-01..N-06) were re-evaluated: N-01 and
N-03 are RESOLVED by cycle 3; all others remain open except as noted. New
findings this cycle: S-01, S-02.

| ID  | Type        | Severity | Summary                                                                 | Recommendation |
| --- | ----------- | -------- | ----------------------------------------------------------------------- | -------------- |
| F-01 | ENVIRONMENT | medium   | config.yaml declares the accounts.0003 dev-superuser (`bob`) bootstrap migration; it does not exist yet | Business decision: implement the migration (fix) or amend config.yaml (regularize) |
| F-02 | ENVIRONMENT | medium   | `manage.py createsuperuser` crashes: UserManager lost create_user/create_superuser via from_queryset | Fix the code: restore manager factory methods |
| F-03 | SPEC→CODE  | medium   | UserQuerySet.create/bulk_create persist plain-text passwords (spec says hashed, never plain-text) | Fix the code (hash on the bulk paths) or scope the spec |
| F-04 | CODE→SPEC  | low      | Direct save() silently refuses an invalid username; contract pinned only by tests | Regularize: add a scenario declaring the save() refusal contract |
| F-05/F-07 | SPEC→CODE/TESTS | low | API trims surrounding whitespace from usernames (201, trimmed); web rejects the same input; no scenario declares either | Business decision, then regularize + align test |
| F-06 | TESTS      | low      | Email duplicate detection is case-sensitive; xfail(strict) test pins an unspecified behavior | Business decision: case-insensitive uniqueness or not |
| F-08 | SPEC→CODE  | low      | `/admin/` route mounted, not described by any living spec | Regularize: one-line note that Django admin is out of scope |
| F-09 | SPEC→CODE  | low      | Authenticated user GETting /web/login/ is redirected to the feed; unspecified | Regularize: add a scenario to "Web session login" |
| F-10 | ENVIRONMENT | low     | Google Fonts and gradient CSS declared in the fixed stack but absent (HTMX resolved in cycle 2) | Regularize: reword config context as target stack, or land them in a UI package |
| N-01 | CODE→SPEC  | —        | Landing placeholder vs posts listing contradiction | **RESOLVED by cycle 3** (MODIFIED deltas aligned both specs with the followed-users feed) |
| N-02 | TESTS      | low      | Scenario "Media stored under the post media path" has no scenario-named test (behavior proven by 4 incidental tests) | Fix the tests: add the scenario-named test |
| N-03 | TESTS      | —        | Missing scenario-named tests for two user-accounts scenarios | **RESOLVED by cycle 3** (test_user_account_persisted, test_logged_in_user_reaches_the_placeholder) |
| N-04 | SPEC→CODE  | low      | API rejects invalid pagination parameters with 400 "Invalid pagination parameters"; no scenario declares it | Regularize: add a scenario to posts "Post listing" |
| N-05 | SPEC→CODE  | medium   | **STILL OPEN** — post-card header links to /web/users/<username>/ (no such route, guaranteed 404) although profiles live at /web/profile/<uuid>/; the href is pinned by test_post_card.py. Cycle 3's claimed resolution did not land | Fix the code: point the card's avatar/username links at web:profile (owner UUID) and update the pinning test; pure code fix restores the living spec's "linked to their profile page" |
| N-06 | CODE→SPEC  | low      | Inline-edit web routing contract (GET 404 unknown/non-owner, non-owner POST 403) pinned only by tests (partially narrowed by cycle 3's "Cancel inline edit") | Regularize: extend posts "Caption update" scenarios |
| S-01 | CODE→SPEC  | low      | web-ui "Active navigation state" requires the rendered page's sidebar entry to be active; profile/following pages mark no entry active (only Home on /web/feed/) | Business decision: regularize Home-only highlighting or extend the template to mark Profile active on profile pages |
| S-02 | CODE→SPEC  | low      | Profile grid items render the full post card (header, caption, actions, menu) while "Profile page structure" declares media + hover overlay only | Business decision: amend the spec to the full-card grid or restrict the grid partial to media+overlay |

Sandbox/verification caveats (not drift): the 2 thread-race attack tests
skip honestly on shared-cache SQLite (invariants separately proven
sequentially and at the DB level); visual rendering, true parallelism, JWT
cryptography, production settings and admin flows remain unverified.
