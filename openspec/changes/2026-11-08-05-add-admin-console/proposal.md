# Proposal — 05-add-admin-console

## Why

With all user-facing capabilities shipped, the project needs a back-office
surface for staff to inspect and manage the domain data (accounts, posts,
stories, follows). The Django admin provides this with almost no code; the
package specifies the guardrails (staff-only access) so the surface is
contractual rather than incidental.

## What Changes

- Register the domain models (`accounts.User`, `posts.Post`,
  `posts.Story`, `social.Follow`) in the Django admin with useful list
  displays and search.
- Enforce staff-only access: anonymous visitors and non-staff users are
  redirected to the admin login.
- Passwords set or edited through the admin MUST be stored hashed (the
  admin's password form handles hashing; raw values are never stored).

## Capabilities

### New Capabilities

- `admin-console`: Staff-only Django admin management of the domain models.

### Modified Capabilities

(none)

## Impact

- Changes confined to `admin.py` registrations and existing admin
  settings; no new apps, models or endpoints.
- The admin sits outside the web UI and REST API contracts: it is a
  back-office tool, not a product surface.
- Tests: the two guardrail scenarios get scenario-named pytest tests;
  coverage stays >= 80%.

## Business Decisions

| Date       | Decision                                                                                                |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | The Django admin is the back-office surface; building a custom admin UI is out of scope for the clone.    |
| 2026-11-08 | Only staff users reach the admin; everyone else is redirected to the admin login.                         |
| 2026-11-08 | Passwords edited through the admin are stored hashed, never in plain text.                                |
