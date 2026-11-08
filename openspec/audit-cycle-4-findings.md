# Cycle 4 audit findings — carried forward to a future cycle

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented for a future cycle. The
living specs are openspec/specs/{user-accounts,web-ui,api-docs,posts,social,
stories}/spec.md; the implemented and archived change is
openspec/changes/archive/2026-11-08-04-add-stories/. All prior findings were
re-evaluated: N-01 and N-03 remain RESOLVED; every other carried finding
remains open. New findings this cycle: W-2 (process), C4-01, C4-02.

| ID  | Type        | Severity | Summary                                                                 | Recommendation |
| --- | ----------- | -------- | ----------------------------------------------------------------------- | -------------- |
| F-01 | ENVIRONMENT | medium   | config.yaml declares the accounts.0003 dev-superuser (`bob`) bootstrap migration; it does not exist yet | Business decision: implement the migration (fix) or amend config.yaml (regularize) |
| F-02 | ENVIRONMENT | medium   | `manage.py createsuperuser` crashes: UserManager lost create_user/create_superuser via from_queryset (verified: AttributeError) | Fix the code: restore manager factory methods |
| F-03 | SPEC→CODE  | medium   | UserQuerySet.bulk_create persists plain-text passwords (verified: stored `plainsecret`); spec says hashed, never plain-text | Business decision: hash on the bulk paths (fix) or scope the spec's "never plain-text" |
| F-04 | CODE→SPEC  | low      | Direct save() silently refuses an invalid username; contract pinned only by tests | Regularize: add a scenario declaring the save() refusal contract |
| F-05/F-07 | SPEC→CODE/TESTS | low | API trims surrounding whitespace from usernames (201, trimmed); web rejects the same input; no scenario declares either | Business decision, then regularize + align test |
| F-06 | TESTS      | low      | Email duplicate detection is case-sensitive; xfail(strict) test pins an unspecified behavior | Business decision: case-insensitive uniqueness or not |
| F-08 | SPEC→CODE  | low      | `/admin/` route mounted, not described by any living spec | Regularize: one-line note that Django admin is out of scope |
| F-09 | SPEC→CODE  | low      | Authenticated user GETting /web/login/ is redirected to the feed; unspecified | Regularize: add a scenario to "Web session login" |
| F-10 | ENVIRONMENT | low     | Google Fonts and gradient CSS declared in the fixed stack but absent (HTMX resolved in cycle 2) | Regularize: reword config context as target stack, or land them in a UI package |
| N-01 | CODE→SPEC  | —        | Landing placeholder vs posts listing contradiction | **RESOLVED by cycle 3**, re-verified in sync |
| N-02 | TESTS      | low      | Scenario "Media stored under the post media path" has no scenario-named test (behavior proven by 4 incidental tests) | Fix the tests: add the scenario-named test |
| N-03 | TESTS      | —        | Missing scenario-named tests for two user-accounts scenarios | **RESOLVED by cycle 3**, re-verified in sync |
| N-04 | SPEC→CODE  | low      | API rejects invalid pagination parameters with 400 "Invalid pagination parameters"; no scenario declares it | Regularize: add a scenario to posts "Post listing" |
| N-05 | SPEC→CODE  | medium   | **STILL OPEN (3rd cycle)** — post-card header links to /web/users/<username>/ (no such route, guaranteed 404) although profiles live at /web/profile/<uuid>/; the href is pinned by test_post_card.py | Fix the code: point the card's avatar/username links at web:profile (owner UUID) and update the pinning test; pure code fix restores the living spec's "linked to their profile page" |
| N-06 | CODE→SPEC  | low      | Inline-edit web routing contract (GET 404 unknown/non-owner, non-owner POST 403) pinned only by tests ("Cancel inline edit" narrows but does not declare the GET/403 cases) | Regularize: extend posts "Caption update" scenarios |
| S-01 | CODE→SPEC  | low      | web-ui "Active navigation state" requires the rendered page's sidebar entry to be active; profile/following pages mark no entry active (only Home on /web/feed/) | Business decision: regularize Home-only highlighting or mark Profile active on profile pages |
| S-02 | CODE→SPEC  | low      | Profile grid items render the full post card (header, caption, actions, menu) while "Profile page structure" declares media + hover overlay only | Business decision: amend the spec to the full-card grid or restrict the grid partial |
| W-1 | SPEC→CODE  | low      | Story endpoints answer non-HTMX POSTs with an undeclared redirect-to-feed fallback (stories spec declares only toast + OOB bar) | Regularize: declare the fallback (one scenario per story requirement) |
| W-2 | PROCESS    | low      | Bad phase overran the 6-run test budget (7/6; two targeted inspection runs), recorded honestly in the archived gbu-state/report | Business decision: whether inspection runs count toward the budget or the budget text is amended |
| C4-01 | CODE→SPEC | low      | Malformed (non-UUID) story identifier falls through the URL converter to a plain 404; the spec's "unknown story identifier" (200 + "Story not found" toast) does not say whether it covers malformed values | Regularize: clarify the malformed-identifier scope in stories "Story view tracking" |
| C4-02 | TESTS     | low      | ORM-level expiry bypass (Story.objects.update()/bulk_create skip the 24h invariant) is pinned only by attack tests; the spec scopes the rule to "the save path" but never declares the bulk-path contract | Regularize: declare the ORM expiry bypass contract in stories "Story data model" |

Sandbox/verification caveats (not drift): the 2 thread-race attack tests skip
honestly on shared-cache SQLite (invariants separately proven sequentially
and at the DB level); visual rendering, true parallelism, JWT cryptography,
production settings, admin flows and interactive docs remain unverified.
