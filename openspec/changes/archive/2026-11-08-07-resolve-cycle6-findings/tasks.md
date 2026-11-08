# Tasks

## 1. user-accounts delta declarations (C6-01, C6-02, C6-04)

- [x] 1.1 Declare the three new scenarios in the delta spec ("API registration trims the email whitespace", "API login trims the username before authentication", "API endpoints accept session-cookie authentication") and add their scenario-named tests in apps/accounts/tests (the session-fallback test asserts an API endpoint answers 200 with a logged-in session client and 401/403 without any token)

  - Manual validation: `POST /api/auth/login/` with `"  bob  "` + correct password → 200; browse `/docs/` logged-in without a token → operations callable.

## 2. Test renames and doc updates (C6-03, C6-05, W-2)

- [x] 2.1 Rename the six sibling-named tests to their exact scenario names (posts "Personal feed on the feed page", "Home feed loads more posts on scroll"; web-ui "Profile link points to own profile", "Login/Register renders the auth card"; social "Web follow failure shows the cause") — assertions unchanged
- [x] 2.2 Update `openspec/config.yaml`: acknowledge the shipped story-ring accent gradient in the frontend line; declare session auth accepted on API endpoints in principle 4; amend the workflow budget policy text in `.opencode/context/workflow.md` (every test-runner execution counts, including inspection runs)
- [x] 2.3 Run the full gates: `pytest` (coverage >= 80%), `ruff check`, `ruff format --check`, `mypy`

## Workflow follow-up

- Archive after review; the delta merges into `openspec/specs/user-accounts/spec.md`.
