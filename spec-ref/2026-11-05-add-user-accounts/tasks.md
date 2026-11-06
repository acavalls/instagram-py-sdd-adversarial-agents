# Tasks

## 1. Project scaffold

- [x] 1.1 Create the Django project skeleton: `config/` with settings split `base/local/test/production`, `manage.py`, `requirements.txt`, `pyproject.toml` (pytest, ruff, mypy, coverage config as in the reference app) and `AUTH_USER_MODEL = "accounts.User"` set before the first migration; verify `manage.py check` passes
- [x] 1.2 Create the `accounts` and `web` apps, register them in `INSTALLED_APPS`, configure `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL` and DRF + SIMPLE_JWT + SPECTACULAR settings as in the reference `config/settings/base.py`; verify `manage.py check` passes with no migrations pending errors

## 2. User model (Requirement: User account data)

- [x] 2.1 Implement `accounts.User` (UUID PK, unique email, bio, profile_pic, `updated_at`) with `validate_registration` classmethod and create the initial migration; verify `manage.py makemigrations --check` and model tests for field constraints pass
- [x] 2.2 Write tests for "User account persisted" and "Username format validation" scenarios in `apps/accounts/tests/test_models.py`, named after the scenarios; verify they pass and coverage >= 80% for `apps`

## 3. Registration (Requirement: User registration)

- [x] 3.1 Implement `UserService.create_user` and `RegisterUserUseCase` (duplicate email/username checks via `validate_registration`, hashed password) with success/failure output dataclasses; verify use case tests for the duplicate-email, duplicate-username and success paths pass
- [x] 3.2 Implement the web register view (`/web/register/`) with the 8-character password rule and success/error toasts, plus `register.html` template in the Instagram card style; verify tests for "Successful registration", "Duplicate email rejected", "Duplicate username rejected" and "Password too short rejected" pass
- [x] 3.3 Implement `UserCreateSerializer` (email, username 3–150 alphanumeric, password min 8, write-only) and `RegisterAPIView` (`POST /api/auth/register/`, 201/400/409); verify tests for "Successful API registration", "API registration conflict" and "API registration validation error" pass

- [x] 3.4 Enforce username format (alphanumeric, 3-150) in the web register view, matching the API serializer rules; verify the "Username format validation" scenario test passes on the web path

## 4. Web session authentication (Requirements: Web session login, Web session logout)

- [x] 4.1 Implement `AuthenticateUserUseCase` with the generic "Invalid credentials" error and the web login view (`/web/login/`) that creates the session, redirects to the feed and shows the success toast; verify tests for "Successful web login" and "Failed web login hides the cause" pass
- [x] 4.2 Implement the logout view (`/web/logout/`) with session clear, redirect and toast, and `login_required` protection on authenticated pages; verify tests for "Successful logout" and "Protected pages require login" pass
- [x] 4.3 Create `login.html` in the Instagram card style with the two-column layout (phone mockup + form) reusing `base_auth.html`; verify the rendered pages contain the expected form fields and error display (template test)

## 5. API JWT authentication (Requirements: API JWT login, API token refresh)

- [x] 5.1 Implement `LoginSerializer` and `LoginAPIView` (`POST /api/auth/login/`) returning user data + access/refresh tokens, 401 with "Invalid credentials" on failure; verify tests for "Successful API login" and "Failed API login" pass
- [x] 5.2 Wire the simplejwt token refresh endpoint into `accounts/urls.py` and verify tests for "Successful token refresh" and "Invalid refresh token rejected" pass

## 6. Integration checks

- [x] 6.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green
- [x] 6.2 Manually verify the OpenAPI schema renders at `/schema/` and Swagger UI at `/docs/` includes register/login/refresh operations

## Workflow follow-up

- Archive the change after review; the delta spec becomes `openspec/specs/user-accounts/spec.md`.
- Verify the archived result with `openspec list --specs`.
