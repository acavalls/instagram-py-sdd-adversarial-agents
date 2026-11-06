# Spec Delta — admin-console (new capability)

## Purpose

Exposes the Django admin as a staff-only management surface for the domain
models (accounts, posts, follows). It is a back-office tool for staff, not a
user-facing product surface, and it sits outside the web UI and REST API
contracts.

## ADDED Requirements

### Requirement: Django admin console
The system SHALL expose the Django admin at `/admin/` for staff users to
manage user accounts, posts and follow relationships. Anonymous visitors and
non-staff users MUST NOT reach the admin pages: the system MUST redirect them
to the admin login.

#### Scenario: Anonymous visitor redirected to admin login
- **WHEN** an anonymous visitor requests `/admin/`
- **THEN** the system responds with the admin login page instead of the admin console

#### Scenario: Staff manages domain models
- **WHEN** a staff user opens the admin console
- **THEN** the system offers management (list, search, edit) of user accounts, posts and follow relationships
