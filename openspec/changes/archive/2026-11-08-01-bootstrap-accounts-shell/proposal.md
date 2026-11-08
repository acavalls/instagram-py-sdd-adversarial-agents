# Proposal — 01-bootstrap-accounts-shell

## Why

The clone has no identity layer and no app shell. Every later capability
(posts, follows, feed, stories) attaches content to a user and is reached
through the authenticated web shell, so this first change must deliver both:
the accounts capability and a minimal **exercisable shell** — a sidebar the
logged-in user can see from the first minute, with declared placeholder
entries for the features that come later. This makes the project manually
validable from change #1 and removes the need for a late "align the shell"
change.

## What Changes

- Create the Django project skeleton (`config/` settings split, `manage.py`,
  requirements, tooling config) with `AUTH_USER_MODEL` set before the first
  migration.
- Introduce the `User` model: UUID primary key, unique username, unique
  email, optional bio and profile picture, hashed password.
- Introduce user registration with duplicate validation (email and
  username), alphanumeric username rule and minimum password length of 8
  characters, with explicit error messages.
- Introduce dual authentication (intentional per project principles):
  - Web UI: login by username with Django session, logout (POST-only),
    session-protected redirects.
  - REST API: `POST /api/auth/register/`, `POST /api/auth/login/` (JWT
    access 30 min / refresh 1 day), token refresh.
- Failed logins return a single generic error ("Invalid credentials").
- Serve the authenticated landing page `/web/feed/` (login required) with a
  **declared placeholder empty state**; the real feed content arrives with
  the social capability.
- Render the authenticated app shell on every logged-in page: fixed left
  sidebar with logo, entries Home, Search, Explore, Messages, Notifications,
  Create, Profile (Search/Explore/Messages/Notifications/Create/Profile are
  **declared placeholder links without destination** until their
  capabilities land), logout form at the bottom, active-state highlight,
  Bootstrap Icons. Authentication pages use a dedicated auth layout without
  the sidebar.
- Expose the OpenAPI schema at `/schema/` and Swagger UI at `/docs/`.

## Capabilities

### New Capabilities

- `user-accounts`: User identity — user model data (including bulk-write
  enforcement of the username rule and byte-exact password comparison),
  registration rules (including concurrency consistency), web session
  authentication, JWT authentication for the REST API, and the
  authenticated landing placeholder.
- `web-ui`: The global web shell — sidebar navigation with declared
  placeholders, active navigation state, icon rendering, auth layout.
- `api-docs`: OpenAPI schema and Swagger UI for the registered endpoints.

### Modified Capabilities

(none — first package of the sequence)

## Impact

- New Django apps: `accounts` (model, services, use cases, serializers, API
  views), `web` (auth views, shell templates).
- API surface: `POST /api/auth/register/` (201/400/409),
  `POST /api/auth/login/` (200/401), token refresh (200/401).
- Dependencies: none beyond the fixed stack already declared in the
  project's `openspec/config.yaml` (`djangorestframework-simplejwt`,
  `drf-spectacular` are part of it).
- Tests: every scenario in each delta spec gets a pytest test traceable by
  scenario name; coverage stays >= 80%.

## Business Decisions

| Date       | Decision                                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | The first change ships accounts AND the exercisable shell: navigation is never deferred to a later change.                                |
| 2026-11-08 | Sidebar entries whose capabilities do not exist yet are declared placeholder links (scenario-pinned), wired later by packages 02 and 03.    |
| 2026-11-08 | Login field is username (Instagram UX), not email.                                                                                        |
| 2026-11-08 | Dual auth kept: sessions for web, JWT for API; unifying them requires an explicit OpenSpec change.                                         |
| 2026-11-08 | Minimum password length is 8 characters; username alphanumeric, 3–150 characters.                                                          |
| 2026-11-08 | The username rule is enforced on every storage path including bulk writes; passwords compare byte-exactly (folded from the original run's regularizations). |
| 2026-11-08 | Logout is POST-only; failed/blank API logins always answer 401 "Invalid credentials" (folded from the original run's regularizations).     |
| 2026-11-08 | Profile editing (bio, profile picture) is out of scope; fields exist on the model without an edit UI.                                      |
| 2026-11-08 | API register returns 409 on duplicate email/username and 400 on validation errors.                                                         |
