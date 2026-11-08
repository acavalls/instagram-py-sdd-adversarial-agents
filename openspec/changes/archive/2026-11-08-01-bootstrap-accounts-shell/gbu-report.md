# GBU Report — 2026-11-08-01-bootstrap-accounts-shell

## Cycle 1 — 2026-11-08

### Executive verdict

RECOMMENDATION: NEXT — every requirement of the three delta specs is
implemented and proven by scenario-traceable tests, all quality gates are
green (111 passed / coverage 99.17% / ruff 0 / mypy 0), the adversarial pass
found and closed 3 blocking bugs, and the second attack survived with only
non-blocking observations.

### Requirement-by-requirement proof

| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| User account data | User account persisted | User model with UUID pk, unique username/email, optional bio/profile_pic, password always hashed on save | apps/accounts/models.py:94-116 | test_user_account_persisted — passed | APPROVED (g2) |
| User account data | Username format validation | Field validator: alphanumeric only, 3–150 chars, enforced at model, web edge and API edge | apps/accounts/models.py:23-30; apps/web/views.py:44-50; apps/accounts/serializers.py:14-34 | test_username_format_validation — passed | APPROVED (g2) |
| User account data | Bulk writes enforce the username rule | Custom QuerySet/Manager intercepts update/bulk_create/bulk_update and validates the username literal before writing | apps/accounts/models.py:52-76 | test_bulk_writes_enforce_the_username_rule_update/_bulk_create/_bulk_update — passed | APPROVED (g2) |
| User account data | Non-literal username write refused | Non-string values (F(), Value(), None) raise the model's username validation error | apps/accounts/models.py:23-30 | test_non_literal_username_write_refused_update_expression/_bulk_create_missing_value — passed | APPROVED (g2) |
| User account data | Legal username bulk write applies | Literal legal usernames pass validation and the write persists | apps/accounts/models.py:52-76 | test_legal_username_bulk_write_applies_update/_bulk_update/_bulk_create — passed | APPROVED (g2) |
| User account data | Password comparison is byte-exact | No trim/fold anywhere; serializer trim_whitespace=False; use case passes the raw password to authenticate() | apps/accounts/serializers.py; apps/accounts/use_cases/authenticate_user.py | test_password_comparison_is_byte_exact; test_login_password_is_byte_exact; test_password_is_stored_and_compared_byte_exactly (Bad regression) — passed | APPROVED (g2 + Bad cycle2) |
| User registration | Successful registration | Use case creates the account; web redirects to /web/login/ with toast "Account created successfully. Please login." | apps/web/views.py:40-41 | test_successful_registration — passed | APPROVED (g2) |
| User registration | Duplicate email rejected | Model validation raises "Email already registered" before the write | apps/accounts/models.py:130-131 | test_duplicate_email_rejected (use case + web) — passed | APPROVED (g2) |
| User registration | Duplicate username rejected | Model validation raises "Username already taken" before the write | apps/accounts/models.py:128-129 | test_duplicate_username_rejected (use case + web) — passed | APPROVED (g2) |
| User registration | Password too short rejected | Both adapters enforce min length 8 with the exact message | apps/web/views.py:13-14; apps/accounts/serializers.py:23-27 | test_password_too_short_rejected; test_api_registration_validation_error_password_too_short — passed | APPROVED (g2) |
| User registration | Concurrent duplicate registration keeps data consistent | DB unique constraints are the last line; the use case maps IntegrityError to the explicit duplicate error | apps/accounts/use_cases/register_user.py:50-57 | test_concurrent_duplicate_registration_keeps_data_consistent (+ username variant) — passed | APPROVED (g2) |
| API registration | Successful API registration | POST /api/auth/register/ → 201 with id/email/username/bio/updated_at | apps/accounts/api_views.py:16-30 | test_successful_api_registration — passed | APPROVED (g2) |
| API registration | API registration conflict | 409 {"error": "Email already registered" / "Username already taken"} | apps/accounts/api_views.py:28-29 | test_api_registration_conflict_email/_username — passed | APPROVED (g2) |
| API registration | API registration validation error | 400 with field-level errors (bad email, short username, short password) | apps/accounts/serializers.py | test_api_registration_validation_error_* — passed | APPROVED (g2) |
| Web session login | Successful web login | Session via django login(), redirect to /web/feed/, toast "Logged in successfully" rendered by the shared messages partial | apps/web/views.py:46-57 | test_successful_web_login; test_login_success_toast_is_rendered_on_feed_page (Bad regression) — passed | APPROVED (g3 + Bad cycle2) |
| Web session login | Failed web login hides the cause | Single generic "Invalid credentials" for wrong password or unknown username | apps/accounts/use_cases/authenticate_user.py:44-45 | test_failed_web_login_hides_the_cause — passed | APPROVED (g3) |
| Web session logout | Successful logout | POST clears the session, redirects to /web/login/, toast "You have been logged out" | apps/web/views.py:64-68 | test_successful_logout — passed | APPROVED (g3) |
| Web session logout | Protected pages require login | @login_required with LOGIN_URL=/web/login/ | apps/web/views.py:71-74 | test_protected_pages_require_login; test_placeholder_requires_login — passed | APPROVED (g3/g4) |
| Web session logout | Logout is POST-only | @require_http_methods(["POST"]) → 405, session untouched | apps/web/views.py:64 | test_logout_is_post_only — passed | APPROVED (g3) |
| API JWT login | Successful API login | 200 with user data + access (30 min) + refresh (1 day) tokens from SIMPLE_JWT settings | apps/accounts/api_views.py:58-81; config/settings/base.py:103-106 | test_successful_api_login — passed | APPROVED (g3) |
| API JWT login | Failed API login | 401 {"error": "Invalid credentials"} | apps/accounts/api_views.py:69-72 | test_failed_api_login — passed | APPROVED (g3) |
| API JWT login | API login with missing fields | Serializer accepts blank/missing; everything lands on the generic 401 | apps/accounts/serializers.py:46-57 | test_api_login_with_missing_fields (blank/missing/empty payload) — passed | APPROVED (g3) |
| API token refresh | Successful token refresh | Valid refresh → 200 {"access": ...} | apps/accounts/api_views.py:93-101 | test_successful_token_refresh — passed | APPROVED (g3) |
| API token refresh | Invalid refresh token rejected | Missing/non-str/invalid/expired → 401, no access token issued | apps/accounts/api_views.py:94-105 | test_invalid_refresh_token_rejected — passed | APPROVED (g3) |
| Authenticated landing placeholder | Placeholder requires login | Anonymous GET /web/feed/ → redirect to login | apps/web/views.py:71-74 | test_placeholder_requires_login — passed | APPROVED (g4) |
| Authenticated landing placeholder | Logged-in user reaches the placeholder | feed.html extends base.html and shows the declared empty state (data-placeholder="feed-empty") | apps/web/templates/web/feed.html:4-8 | test_logged_in_user_reaches_the_placeholder — passed | APPROVED (g4) |
| Sidebar navigation | Sidebar renders navigation for authenticated user | Fixed left sidebar with logo + 7 entries + logout form, gated on user.is_authenticated | apps/web/templates/web/base.html:12-63 | test_sidebar_renders_navigation_for_authenticated_user — passed | APPROVED (g4) |
| Sidebar navigation | Placeholder entries have no destination | Six entries are <a> without href (aria-disabled) | apps/web/templates/web/base.html:24-53 | test_placeholder_entries_have_no_destination — passed | APPROVED (g4) |
| Sidebar navigation | Logo links to the home feed | Logo anchors to /web/feed/ | apps/web/templates/web/base.html:15 | test_logo_links_to_the_home_feed — passed | APPROVED (g4) |
| Sidebar navigation | Logout available at the sidebar bottom | POST form with CSRF at the sidebar bottom | apps/web/templates/web/base.html:55-61 | test_logout_available_at_the_sidebar_bottom — passed | APPROVED (g4) |
| Sidebar navigation | Anonymous pages render without sidebar | Auth layout has no sidebar; sidebar additionally gated on authentication | apps/web/templates/web/base_auth.html | test_anonymous_pages_render_without_sidebar — passed | APPROVED (g4) |
| Active navigation state | Active link reflects current page | Only Home gets .active on the feed page | apps/web/templates/web/base.html:19 | test_active_link_reflects_current_page — passed | APPROVED (g4) |
| Icon rendering | Icon font is loaded | Bootstrap Icons stylesheet on every page (both base templates) | apps/web/templates/web/base.html:8; base_auth.html:8 | test_icon_font_is_loaded — passed | APPROVED (g4) |
| Auth layout | Login renders the auth card | auth-page body, centered card with logo + form, secondary card to register, footer links, no sidebar | apps/web/templates/web/login.html; base_auth.html | test_login_page_renders_form (extended with logo assertions) — passed | APPROVED (g4 iter2) |
| Auth layout | Register renders the auth card | Card with logo + form, secondary card to login, footer links, no sidebar | apps/web/templates/web/register.html | test_register_page_renders_auth_layout — passed | APPROVED (g4 iter2) |
| OpenAPI documentation | Schema endpoint serves the API contract | /schema/?format=json → 200 OpenAPI 3.x with POST register/login/refresh | config/urls.py:10; apps/accounts/api_views.py @extend_schema | test_schema_endpoint_serves_the_api_contract — passed | APPROVED (g5) |
| OpenAPI documentation | Docs UI renders | /docs/ → 200 Swagger UI bound to the schema | config/urls.py:11 | test_docs_ui_renders — passed | APPROVED (g5) |

### Quality gates (actual results)

pytest 111 passed, 1 xfailed (documented MEDIUM observation), 0 failed ·
coverage 99.17% (target >= 80) · ruff check: 0 issues · ruff format --check:
clean · mypy: 0 errors in 47 source files · manage.py check: no issues ·
makemigrations --check: no changes detected.

### Adversarial pass (The Bad)

- Cycle 1 (BROKEN):
  - ATK-001 bulk-write gate bypass (str subclass/bytes/expressions, post-construction mutation, thread-local leak) → survived.
  - ATK-002 direct instance save() with invalid username → bug BUG-001 (HIGH) found → fixed (User.save() validates the username and refuses the write; also hashes plain-text passwords on save) → regression tests in apps/accounts/tests/test_bad_attack_storage_bypass.py in the suite.
  - ATK-003 toast rendering across redirects → bug BUG-002 (HIGH) found → fixed (shared partial web/partials/messages.html included by both base templates) → regression test in apps/web/tests/test_bad_attack_toasts_and_edges.py.
  - ATK-006 malformed API payloads → bug BUG-003 (HIGH) found → fixed (trim_whitespace=False on password serializers) → regression test in apps/accounts/tests/test_bad_attack_api_malformed.py.
  - ATK-004 cross-site logout CSRF, ATK-005 email-case duplicates, ATK-007 JWT cross-use → survived.
- Cycle 2 (SURVIVES, final iteration):
  - ATK-001..008 (silent-refusal contract, update_fields bypass, double-hashing, manager flows, toast-once, escaping, byte-exact spaced passwords) → all held; 3 new regression files joined the suite (test_bad_attack_cycle2_*).
  - Non-blocking observations (MEDIUM, recorded, no fix loop): (1) UserManager lost create_user/create_superuser via from_queryset → `manage.py createsuperuser` crashes (spec-silent; the only bootstrap is the accounts.0003 migration per config.yaml, not yet in this change's scope); (2) set_unusable_password() + save() re-hashes the unusable marker (developer path, spec-silent); (3) identify_hasher heuristic can store a raw password that parses as a hasher format via direct save (developer path, registration unaffected); (4) bulk_create/queryset.update still persist plain-text passwords (spec scopes "every storage path" to the username rule only); (5) username trimming differs between API (trims) and web (rejects) adapters — stored value always valid.
  - Budget: 6 min + 6 runs (cycle 1), 5 min + 6 runs (cycle 2) — limits per cycle: 6 min, 6 runs, 2 iterations.

### Deviations and assumptions

- Direct save() with an invalid username REFUSES THE WRITE SILENTLY (no
  exception), matching the Bad's regression-test contract; bulk writes raise
  the model's validation error as the spec pins. Agent-decided, flagged for
  review: a caller-friendly alternative would raise the same ValidationError
  on save(); the observable spec scenarios are satisfied either way.
- User.save() hashes any plain-text password before persisting (spec: "a
  hashed (never plain-text) password"); bulk_create bypasses save() and can
  still store plain text (observation 4 above).
- The feed landing was implemented as a stub in group 3 (to make
  "Protected pages require login" exercisable) and replaced by the real
  placeholder template in group 4, as planned.
- Refresh endpoint is a thin wrapper so a MISSING refresh token answers 401
  (simplejwt's stock view would answer 400); rejection body {"error":
  "Invalid refresh token"} (unspecified by the spec).
- Register's success redirect targets /web/login/ before that route existed
  (group 2); it exists since group 3 — resolved inside the same change.
- Group 4 iteration 1 was REJECTED by Ugly (auth cards missing logo, register
  missing secondary card/footer); fixed in iteration 2 and re-approved.
- MEDIUM observation on email case-sensitivity duplicates is encoded as an
  xfail (strict) test pending a future spec decision.

### Manual validation pointers (mandatory when the change declares an interface)

The change declares three human-exercisable surfaces:

1. Web UI (dev server: `.venv/bin/python manage.py migrate && .venv/bin/python manage.py runserver`):
   - Register: open http://localhost:8000/web/register/ → create a user
     (e.g. `alice` / `alice@example.com` / `password123`) → expect redirect
     to /web/login/ with the toast "Account created successfully. Please
     login." Repeat with the same email → expect "Email already registered";
     with a 5-char password → "Password must be at least 8 characters".
   - Login: at /web/login/ enter `alice` / `password123` → expect redirect to
     /web/feed/ with the toast "Logged in successfully" and the sidebar
     (logo, Home highlighted, Search/Explore/Messages/Notifications/Create/
     Profile as inert links, logout form at the bottom). Wrong password →
     "Invalid credentials" only.
   - Logout: POST form at the sidebar bottom → redirect to /web/login/ with
     the toast "You have been logged out"; anonymous /web/feed/ redirects to
     login.
   - Placeholder wiring state: the feed shows the declared empty state
     ("Your feed is empty"); the six sidebar entries have no destination —
     replacing them is a tracked observable change of packages 02/03.
2. REST API (curl):
   - `curl -X POST http://localhost:8000/api/auth/register/ -H 'Content-Type: application/json' -d '{"username":"bob","email":"bob@example.com","password":"password123"}'` → 201 with id/email/username/bio/updated_at; repeating → 409.
   - `curl -X POST http://localhost:8000/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"bob","password":"password123"}'` → 200 with user data + access + refresh; wrong password → 401 "Invalid credentials".
   - `curl -X POST http://localhost:8000/api/auth/refresh/ -H 'Content-Type: application/json' -d '{"refresh":"<refresh token>"}'` → 200 with a new access token; garbage → 401.
3. API docs: open http://localhost:8000/docs/ → Swagger UI lists POST
   /api/auth/register/, /api/auth/login/, /api/auth/refresh/; try login from
   the UI → 200 with tokens. http://localhost:8000/schema/?format=json →
   OpenAPI JSON with the same operations.
   Placeholder wiring state: only auth operations exist in the schema; posts
   paths arrive with package 02 (MODIFIED delta).

### Sheriff decision

[ ] SI — proceed to verify/archive
[ ] NO — <reason> → /opsx-update (artifacts wrong) or re-apply
