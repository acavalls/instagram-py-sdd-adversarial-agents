# Tasks

Ordering premise: inside-out WITHIN each task; each group is
validation-closed, with its Manual validation line.

## 1. Admin registrations and guardrails (Requirement: Django admin console)

- [x] 1.1 Register `accounts.User`, `posts.Post`, `posts.Story` and `social.Follow` in their apps' `admin.py` with list displays and search; verify `manage.py check` passes
- [x] 1.2 Tests: anonymous visitor redirected to the admin login, staff manages the four domain models, admin-set passwords are stored hashed and validate with `check_password`

  - Manual validation: log in as a staff user (`/admin/`), browse the four
    models (list, search, edit); change a user's password and confirm the
    user can log in with it from the web UI; open `/admin/` in an
    anonymous window and see the login page.

## 2. Quality gates

- [x] 2.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green

## Workflow follow-up

- Archive the change after review; the delta merges into
  `openspec/specs/admin-console/spec.md`.
