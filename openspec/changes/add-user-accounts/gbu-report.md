# GBU Report — add-user-accounts

## Cycle 1 — 2026-11-06

### Executive verdict

RECOMMENDATION: NEXT — All 14 tasks implemented, every delta-spec scenario
proven by a passing test named after it, all quality gates green
(72 tests, 100% coverage), one Ugly rejection fixed within budget, and 29
adversarial attacks from The Bad survived with zero bugs found.

### Requirement-by-requirement proof

| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| User account data | User account persisted | `User(AbstractUser)` with UUID PK, unique username/email, optional bio/pic, hashed password; initial migration | apps/accounts/models.py:20-27, migrations/0001_initial.py | test_user_account_persisted (apps/accounts/tests/test_models.py) — PASS | APPROVED |
| User account data | Username format validation | `validate_registration`/`validate_username_format`: 3–150 alphanumeric, exact spec messages | apps/accounts/models.py:33-43 | test_username_format_validation (test_models.py, web + API variants) — PASS | APPROVED |
| User registration | Successful registration | Web view pre-checks field formats, use case creates hashed-password user, redirect to login + toast | apps/web/views.py (register), templates/web/register.html | test_successful_registration — PASS | APPROVED (iter 2) |
| User registration | Duplicate email rejected | Model-level duplicate check returns "Email already registered" | apps/accounts/models.py:59-60 | test_duplicate_email_rejected (web) — PASS | APPROVED |
| User registration | Duplicate username rejected | Model-level duplicate check returns "Username already taken" | apps/accounts/models.py:57-58 | test_duplicate_username_rejected (web) — PASS | APPROVED |
| User registration | Password too short rejected | Min-8 rule enforced in web view AND API serializer (design decision 2) | apps/web/views.py:30-31, apps/accounts/serializers.py:35-40 | test_password_too_short_rejected — PASS | APPROVED |
| User registration | (web) Username format validation | Web pre-check via `validate_username_format` before use case | apps/web/views.py:32-35 | test_username_format_validation (web view) — PASS | APPROVED |
| Web session login | Successful web login | `AuthenticateUserUseCase` + `auth.login()` creates session, redirect to feed + "Logged in successfully" | apps/web/views.py:79-98 | test_successful_web_login — PASS (session `_auth_user_id` asserted) | APPROVED |
| Web session login | Failed web login hides the cause | Generic error constant in use case; wrong password AND unknown username produce identical "Invalid credentials" | apps/accounts/use_cases.py:13,80 | test_failed_web_login_hides_the_cause + unknown-username parity test — PASS | APPROVED |
| Web session logout | Successful logout | `auth.logout()` clears session, redirect to login + "You have been logged out" | apps/web/views.py:101-105 | test_successful_logout — PASS (session cleared asserted) | APPROVED |
| Web session logout | Protected pages require login | `@login_required` on feed placeholder; anonymous → LOGIN_URL with next param | apps/web/views.py:108-111 | test_protected_pages_require_login — PASS | APPROVED |
| API registration | Successful API registration | RegisterAPIView → 201 with id/email/username/bio/updated_at; password write-only | apps/accounts/api_views.py, serializers.py | test_successful_api_registration — PASS (no password echo) | APPROVED (iter 2) |
| API registration | API registration conflict | Use case error → 409 with "Email already registered"/"Username already taken" | apps/accounts/api_views.py:32-33 | test_api_registration_conflict — PASS (both branches) | APPROVED (iter 2) |
| API registration | API registration validation error | Serializer field rules → 400 field-level errors | apps/accounts/serializers.py:28-40 | test_api_registration_validation_error — PASS | APPROVED (iter 2) |
| API JWT login | Successful API login | `RefreshToken.for_user`, 200 with user data + access + refresh; `user_id` claim = UUID PK | apps/accounts/api_views.py:47-80 | test_successful_api_login — PASS (token decode asserted) | APPROVED |
| API JWT login | Failed API login | 401 with generic "Invalid credentials", delegated to use case | apps/accounts/api_views.py:63-70 | test_failed_api_login — PASS (both branches) | APPROVED |
| API token refresh | Successful token refresh | Thin simplejwt `TokenRefreshView` subclass at /api/auth/refresh/ | apps/accounts/api_views.py:83-96 | test_successful_token_refresh — PASS | APPROVED |
| API token refresh | Invalid refresh token rejected | Missing (400) and garbage (401) rejected; no `access` key in either | apps/accounts/tests/test_views.py:130-139 | test_invalid_refresh_token_rejected — PASS | APPROVED |

### Quality gates (actual results)

pytest 72/72 passed · coverage 100.00% for apps/ (target >= 80) ·
ruff check: 0 issues · ruff format --check: 86 files formatted ·
mypy: 0 errors (34 source files) · manage.py check: 0 issues ·
makemigrations --check: no changes detected ·
manage.py spectacular: 0 errors, 0 warnings (register/login/refresh in schema)

### Adversarial pass (The Bad)

29 attacks, all survived; zero bugs found. Highlights:
- ATK-001/002 malformed JSON / wrong content type → 4xx, never 500
- ATK-003 injected is_staff/is_superuser/extra fields → ignored (mass-assignment safe)
- ATK-004/022 password never echoed nor stored in plaintext
- ATK-005/006/018/019 boundary values (username 2/3/150/151 chars, unicode, password 7/8 chars) → exact spec messages
- ATK-007/020 duplicate double-submits → 409 / exact messages, single row
- ATK-008/023 generic-error equivalence for blank/wrong/unknown credentials
- ATK-013/014 refresh lifecycle: valid/garbage/missing/blank/expired/tampered → never issues an access token on failure
- ATK-025/027/028 corrupted session cookie → redirect (no 500); XSS payloads via login/register re-render → auto-escaped
- ATK-024/026 logout twice, login again, anonymous vs authenticated feed access
- Regression files added to the suite: apps/accounts/tests/test_bad_attacks_api.py, apps/web/tests/test_bad_attacks_web.py
- Budget: 6 min used, 6 test runs (limits: 10 min, 10 runs, 3 iterations)

Minor spec-silent observations (documented, no action required for this change):
- Web view strips username but not password; API strips both (padded-password cross-path mismatch)
- API login returns 400 (field errors) for blank/missing fields vs 401 for wrong credentials — no cause leak
- Duplicate detection is check-then-act: a true concurrent race would surface as 500 (DB unique constraints prevent corruption); not reproducible deterministically with SQLite test transactions
- GET /web/logout/ performs a state change without CSRF (Django recommends POST-only logout)

### Ugly audit history

- Group 1 (scaffold): APPROVED iter 1. Deviation accepted: User model fields defined in group 1 (Django auth.E003 hard-fails `manage.py check` if AUTH_USER_MODEL points to a non-existent model); validate_registration + migration correctly deferred to group 2.
- Group 2 (user model): APPROVED iter 1.
- Group 3 (registration): REJECTED iter 1 — ACT-001: web view omitted the email-shape pre-check required by design decision 2 (web path silently persisted malformed emails). Fixed iter 2 (validate_email + parity message + test) → APPROVED.
- Group 4 (web session auth): APPROVED iter 1. Feed page is a minimal login_required placeholder (feed belongs to a later change).
- Group 5 (API JWT): APPROVED iter 1.
- Group 6 (integration checks): APPROVED — RegisterAPIView extend_schema added (metadata only) to silence the spectacular graceful-fallback error; new schema test asserts register/login/refresh operations at /schema/.

### Deviations and assumptions

- Feed page is a trivial `login_required` placeholder (no feed business logic): LOGIN_REDIRECT_URL and the "Protected pages require login" scenario needed a concrete target; the real feed belongs to the later posts/feed change.
- `validate_registration` returns error strings (str | None) instead of raising: consumed directly by the use case dataclass outputs (design decision 6).
- Length error message is "Username must be between 3 and 150 characters" (spec allows "an equivalent length error" for the length branch).
- Refresh endpoint routed at /api/auth/refresh/ (not simplejwt's default /api/auth/token/refresh/) for consistency with the flat /api/auth/ prefix.
- Expired-refresh-token rejection tested via a crafted past-exp token rather than waiting a real lifetime.
- RegisterAPIView @extend_schema documents only the 201 response (400/409 branches undocumented in the schema — same as before the fix).
- Ruff excludes migrations directories; .opencode excluded from ruff (owned docs).
- Web register redirects to the literal /web/login/ (login view did not exist when group 3 landed).

### Manual validation pointers (optional for the Sheriff)

- `source .venv/bin/activate && python manage.py migrate && python manage.py runserver`, then visit http://127.0.0.1:8000/web/register/ and http://127.0.0.1:8000/web/login/ (Instagram-style cards, toasts on success/failure).
- Swagger UI: http://127.0.0.1:8000/docs/ (register/login/refresh operations).
- Full suite: `.venv/bin/pytest` (72 tests, ~3 s).

### Sheriff decision

[ ] SI — proceed to verify/archive
[ ] NO — <reason> → /opsx-update (artifacts wrong) or re-apply
