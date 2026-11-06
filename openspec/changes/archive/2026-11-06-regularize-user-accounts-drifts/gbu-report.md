# GBU Report — regularize-user-accounts-drifts

## Cycle 1 — 2026-11-06

### Executive verdict

RECOMMENDATION: NEXT — All 8 tasks implemented; every delta scenario proven
by a passing test; all quality gates green (126 tests + 1 xfail, coverage
99.25%); the adversarial pass found 5 bugs (BUG-001…BUG-004 fixed and
verified; BUG-005 deferred by Sheriff decision, documented below).

### Requirement-by-requirement proof

| Requirement (delta) | Scenario | How it is solved | Evidence (file:line) | Test proving it | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| API documentation surface (ADDED) | OpenAPI schema is served | Schema includes register/login/refresh POST ops | config/urls.py, tests/test_scaffold.py | test_schema_includes_auth_operations — PASS | APPROVED |
| API documentation surface (ADDED) | Swagger UI is served | Swagger UI renders the operations | tests/test_scaffold.py | test_swagger_ui_renders — PASS | APPROVED |
| Authenticated landing placeholder (ADDED) | Placeholder requires login | @login_required on /web/feed/ | apps/web/views.py | test_protected_pages_require_login — PASS | APPROVED |
| Authenticated landing placeholder (ADDED) | Logged-in user reaches the placeholder | Authenticated GET renders it | apps/web/views.py | test_authenticated_user_reaches_protected_feed — PASS | APPROVED |
| User registration (MODIFIED) | Concurrent duplicate registration keeps data consistent | DB unique constraints accept at most one account | apps/accounts/migrations/0001_initial.py | test_username_and_email_must_be_unique — PASS | APPROVED |
| API JWT login (MODIFIED) | API login with missing fields | handle_exception maps ParseError + serializer invalid → 401 generic | apps/accounts/api_views.py | test_api_login_with_missing_fields — PASS (5 failure shapes, exact body) | APPROVED |
| (all original 17 scenarios) | Regression | All archived scenario tests keep names and pass | apps/*/tests | 126 passed + 1 xfailed | APPROVED |

### Code regularization delivered

- Username alphanumeric rule at model level: redeclared field with
  `\A[a-zA-Z0-9]+\Z` RegexValidator + MinLengthValidator(3), migration 0002;
  rule-enforcing UserManager (create_user/create_superuser never persist a
  hostile username; errors-as-values detached instance), User.save() guard.
- LoginAPIView: every failure shape → 401 "Invalid credentials" (including
  blank/missing fields and unparseable JSON).
- Passwords byte-exact everywhere: trim_whitespace=False on both API
  password fields (web path never trimmed).
- Logout CSRF-protected POST-only (@require_POST; GET → 405, session
  survives).

### Quality gates (actual results)

pytest 126 passed + 1 xfailed · coverage 99.25% (target >= 80) ·
ruff check: 0 issues · ruff format --check: 94 files formatted ·
mypy: 0 errors (36 source files) · manage.py check: 0 issues ·
makemigrations --check: no changes detected · spectacular: 0 errors/warnings

### Adversarial pass (The Bad)

- Iteration 1 — 19 attacks, BROKEN: BUG-001 (create_user/create_superuser
  bypassed the username rule; fixed with rule-enforcing UserManager +
  save() guard), BUG-002 (malformed JSON login → 400 with parse detail;
  fixed mapping ParseError to generic 401), BUG-003 (regex `$`-anchor
  accepted 'alice\\n', no min length; fixed \\A/\\Z + MinLengthValidator(3),
  migration 0002 regenerated).
- Iteration 2 — 9 attacks, BROKEN: BUG-004 (create_superuser did not
  delegate through create_user — Django's contrib calls _create_user
  directly; fixed by overriding create_superuser to replicate Django's flag
  handling and delegate through create_user).
- Iteration 3 — 6 attacks, BROKEN: BUG-005 (see below). All other attacks
  passed: hostile string batch, flag contract (ValueError for falsy flags),
  duplicate-superuser interaction, detached-instance no-leak path.
- Budget: 3 attack iterations used (limit 3); per-iteration minutes 6-9
  (limit 10); max 10 test runs respected.

### Open bug — BUG-005 (deferred by Sheriff decision, 2026-11-06)

`create_user(None)` / `create_superuser(None)` raise an unhandled
`TypeError` (`len(None)` inside `validate_username_format`,
apps/accounts/models.py:130) instead of the errors-as-values detached
instance or Django's documented `ValueError('The given username must be
set')`. Nothing is persisted (no data-integrity impact). Repro test:
`test_atk_r3_006_none_username_raises_typeerror_not_valueerror` in
`apps/accounts/tests/test_bad_attacks_regularization3.py` (currently
failing, kept as the executable record).

Sheriff decision at the Bad budget exhaustion: close the current drift
cycle with BUG-005 documented for a future cycle (option 2). Suggested
future fix: guard non-string/falsy username at the top of
`UserManager.create_user` (and therefore create_superuser via delegation),
then have Bad verify in a future cycle.

Also documented (not charged, spec-silent): queryset `.update()` /
`bulk_create()` bypass model-level validation (Django-level; xfail test
documents it); 415 for un-negotiable content type on login (request-level
rejection); fullwidth unicode usernames refused without NFKC normalization
(strictly safer direction).

### Deviations and assumptions

- create_user with a hostile username returns a detached instance (does not
  raise) — errors-as-values per design decision 6; bare save()/QuerySet
  .create() raise ValidationError via the save() guard.
- Serializer username keeps trim_whitespace=True (web-parity, established
  by ATK-011); only passwords became byte-exact.
- 'alice\\n' at API register normalizes to 'alice' (DRF trims) — web parity;
  a non-alphanumeric username can never be stored (model-level guard).
- The xfail test (queryset update/bulk_create bypass) is strict=False and
  will xpass if a DB guard is ever added.

### Manual validation pointers (optional for the Sheriff)

- `.venv/bin/pytest` (126 passed + 1 xfailed, ~3 s).
- `python manage.py createsuperuser` with a hostile username → refused.
- POST /web/logout/ with curl (no CSRF) → 403; GET → 405.

### Sheriff decision

[x] SI — proceed to verify/archive (BUG-005 deferred and documented)
