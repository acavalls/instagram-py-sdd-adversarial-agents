# Proposal

## Why

The Instagram clone currently has no specified identity layer. Every other
capability of the reference app (posts, follows, feed, stories, suggestions)
attaches content to a user, so user accounts are the foundation capability and
must be specified first. Specifying it now establishes the traceability
pattern (scenario-named tests, living specs) that all later changes will
follow.

## What Changes

- Introduce the `User` model: UUID primary key, unique username, unique email,
  optional bio and profile picture, hashed password.
- Introduce user registration with duplicate validation (email and username),
  alphanumeric username rule and minimum password length of 8 characters,
  with explicit error messages.
- Introduce dual authentication (intentional per project principles):
  - Web UI: login by username with Django session, logout, session-protected
    redirects.
  - REST API: login returning a JWT token pair (access 30 min / refresh 1 day)
    under `POST /api/auth/login/`, plus registration under
    `POST /api/auth/register/`.
- Failed logins return a single generic error ("Invalid credentials") and
  never reveal whether the username or the password was wrong.
- Introduce the login and register pages styled after Instagram
  (templates + HTMX layout).

## Capabilities

### New Capabilities

- `user-accounts`: User identity — user model data, registration rules,
  web session authentication (login/logout) and JWT authentication for the
  REST API.

### Modified Capabilities

(none — first change in the project)

## Impact

- New Django apps: `accounts` (model, services, use cases, serializers, API
  views), `web` (login/register/logout views and templates), `api` (root
  endpoint later; JWT auth wired through DRF settings).
- API surface: `POST /api/auth/register/` (201/400/409),
  `POST /api/auth/login/` (200/401). Refresh endpoint comes from
  `djangorestframework-simplejwt` defaults.
- Dependencies: none beyond the fixed stack already declared in
  `openspec/config.yaml` (djangorestframework-simplejwt is part of it).
- Tests: every scenario in the delta spec gets a pytest test traceable by
  scenario name; coverage stays >= 80%.

## Business Decisions

| Date       | Decision                                                                                        |
| ---------- | ----------------------------------------------------------------------------------------------- |
| 2026-11-04 | First change covers accounts only; posts, follows, feed and stories are later changes.          |
| 2026-11-04 | Login field is username (Instagram UX), not email.                                              |
| 2026-11-04 | Dual auth kept: sessions for web, JWT for API; unifying them requires an explicit OpenSpec change. |
| 2026-11-04 | Minimum password length is 8 characters (matches reference app, both web and API).              |
| 2026-11-04 | Username must be alphanumeric, 3–150 characters (matches API serializer of the reference app).   |
| 2026-11-04 | Profile editing (bio, profile picture) is out of scope; fields exist on the model without an edit UI, matching the reference app. |
| 2026-11-04 | API register returns 409 on duplicate email/username and 400 on validation errors.              |
