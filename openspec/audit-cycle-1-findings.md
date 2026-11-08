# Cycle 1 audit findings — carried forward to a future cycle

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented for a future cycle. The
living specs are openspec/specs/{user-accounts,web-ui,api-docs}/spec.md;
the implemented and archived change is
openspec/changes/archive/2026-11-08-01-bootstrap-accounts-shell/.

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
| F-10 | ENVIRONMENT | low     | HTMX, Google Fonts and gradient CSS declared in the fixed stack but absent from the code | Regularize: reword config context as target stack, or land them in a package |

Not verified by the audit: visual rendering, Django admin flows, production
settings, JWT cryptographic details, real-parallelism concurrency.
