# Tasks

Ordering premise: inside-out WITHIN each task (model → service → use case →
adapter); each group is validation-closed — when it ends, what it
introduces is exercisable end-to-end, and the Manual validation line says
how a human proves it.

## 1. Project scaffold

- [x] 1.1 Create the Django project skeleton: `config/` with settings split `base/local/test/production`, `manage.py`, `requirements.txt`, `pyproject.toml` (pytest, ruff, mypy, coverage config) and `AUTH_USER_MODEL = "accounts.User"` set before the first migration; verify `manage.py check` passes
- [x] 1.2 Create the `accounts` and `web` apps, register them in `INSTALLED_APPS`, configure `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL` and DRF + SIMPLE_JWT + SPECTACULAR settings; create the base templates (`base_auth.html`, `base.html` shell skeleton with the `#messages`/`#modal-container` mount points) and load Bootstrap Icons; verify `manage.py check` passes and the dev server boots

  - Manual validation: `manage.py runserver` boots without errors.

## 2. User model and registration (Requirement: User account data, User registration)

- [x] 2.1 Implement `accounts.User` (UUID PK, unique email, bio, profile_pic, `updated_at`) with `validate_registration` classmethod enforcing the username rule and byte-exact password handling on every storage path (including bulk writes); create the initial migration; verify `manage.py makemigrations --check` and model tests for field constraints and bulk-write refusals pass
- [x] 2.2 Implement `UserService.create_user` and `RegisterUserUseCase` (duplicate checks, hashed password) with success/failure output dataclasses; verify use case tests for duplicate-email, duplicate-username, concurrency and success paths pass
- [x] 2.3 Implement the web register view (`/web/register/`) with the 8-character password rule, username format rule and success/error toasts, plus `register.html` in the auth layout; verify tests for "Successful registration", "Duplicate email rejected", "Duplicate username rejected", "Password too short rejected" and "Username format validation" pass
- [x] 2.4 Implement `UserCreateSerializer` and `RegisterAPIView` (`POST /api/auth/register/`, 201/400/409); verify tests for "Successful API registration", "API registration conflict" and "API registration validation error" pass

  - Manual validation: open `/web/register/`, register a user (see the
    success toast), repeat with the same email (see "Email already
    registered"); `curl -X POST /api/auth/register/ -d '{"username":"u1","email":"u1@x.com","password":"password123"}' -H 'Content-Type: application/json'` returns 201; repeating it returns 409.

## 3. Web session and JWT authentication (Requirements: Web session login, Web session logout, API JWT login, API token refresh)

- [x] 3.1 Implement `AuthenticateUserUseCase` with the generic "Invalid credentials" error and the web login view (`/web/login/`) that creates the session, redirects to the feed and shows the success toast; verify tests for "Successful web login", "Failed web login hides the cause" and "API login with missing fields" pass
- [x] 3.2 Implement the logout view (`/web/logout/`, POST-only) with session clear, redirect and toast, and `login_required` protection on authenticated pages; verify tests for "Successful logout", "Protected pages require login" and "Logout is POST-only" pass
- [x] 3.3 Create `login.html` in the auth layout (two-column card, secondary card to register); verify the rendered pages contain the expected form fields and error display
- [x] 3.4 Implement `LoginAPIView` (`POST /api/auth/login/`) and wire the simplejwt refresh endpoint; verify tests for "Successful API login", "Failed API login", "Successful token refresh" and "Invalid refresh token rejected" pass

  - Manual validation: log in via `/web/login/` (redirects to `/web/feed/`,
    toast "Logged in successfully"); log out via the auth layout footer
    (toast "You have been logged out"); `curl -X POST /api/auth/login/ -d '{"username":"u1","password":"password123"}' -H 'Content-Type: application/json'` returns tokens; refresh one of them.

## 4. Exercisable shell and landing placeholder (Requirements: Sidebar navigation, Active navigation state, Icon rendering, Auth layout, Authenticated landing placeholder)

- [x] 4.1 Complete `base.html` with the fixed left sidebar: logo to the feed, entries Home (active-state aware), Search, Explore, Messages, Notifications, Create, Profile as declared placeholder links, logout form at the bottom, `#messages` and `#modal-container` preserved; responsive CSS (collapse at <=1024px, bottom bar at <=768px); re-parent the feed landing on `base.html`; verify tests for "Sidebar renders navigation for authenticated user", "Placeholder entries have no destination", "Logo links to the home feed", "Logout available at the sidebar bottom", "Anonymous pages render without sidebar" and "Active link reflects current page" pass
- [x] 4.2 Implement the landing view `/web/feed/` (login required) rendering the declared placeholder empty state; verify tests for "Placeholder requires login" and "Logged-in user reaches the placeholder" pass

  - Manual validation: log in → the sidebar renders with all entries;
    Search/Explore/Messages/Notifications/Create/Profile are inert links;
    Home is highlighted on the landing page; the landing shows the
    placeholder empty state; opening `/web/feed/` in an anonymous window
    redirects to login.

## 5. API documentation surface (Requirement: OpenAPI documentation)

- [x] 5.1 Verify `/schema/` renders (JSON with `?format=json`) including the register/login/refresh operations and `/docs/` renders the Swagger UI (schema test)

  - Manual validation: open `/docs/` in a browser and try the login
    operation from the Swagger UI.

## 6. Quality gates

- [x] 6.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green

## Workflow follow-up

- Archive the change after review; the deltas become
  `openspec/specs/{user-accounts,web-ui,api-docs}/spec.md`.
- Verify the archived result with `openspec list --specs`.
