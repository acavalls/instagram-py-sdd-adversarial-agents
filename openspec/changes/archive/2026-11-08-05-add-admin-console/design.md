# Design

## Context

The clone runs all user-facing capabilities (packages 01–04). This is a
small back-office package with no product-surface impact.

## Goals / Non-Goals

**Goals:**

- Make the Django admin a specified, guarded surface for the domain models.
- Keep the change minimal: registrations and access guardrails only.

**Non-Goals:**

- Custom admin UI, dashboards, bulk tooling beyond Django admin defaults.
- Role management beyond Django's `is_staff` flag.
- Any change to the web UI or REST API contracts.

## Decisions

1. **Django admin as-is** (`django.contrib.admin`): model registrations
   with list display/search; no custom views. Alternative considered: a
   custom staff UI — rejected as over-engineering for the clone.

2. **Staff-only access** is Django's default admin behavior (login
   redirect); it is pinned by scenarios so it stays contractual.

3. **Hashed password handling** through the admin's password form; a test
   asserts that a password set via the admin validates with
   `check_password` and is never stored raw.

## Dependency-wiring map

| Capability (this package) | Depends on | Not yet implemented? | Minimal wiring planned |
| ------------------------- | ---------- | -------------------- | ---------------------- |
| Admin console             | All domain models | No (packages 01–04) | — |

## Risks / Trade-offs

- [Admin surface drifts from the domain] → Registrations cover exactly the
  four domain models; new models require a spec delta to appear here.

## Migration Plan

None (no models change).

## Open Questions

None.
