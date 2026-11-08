# Tasks

## 1. user-accounts declarations and test alias (C7-01, C7-02, C7-03)

- [x] 1.1 Declare the session-precedence/CSRF and anonymous-403 semantics in the delta ("API JWT login" text + 3 new scenarios) and add their scenario-named tests (session wins over a foreign JWT + CSRF on unsafe session methods; anonymous request → 403 without WWW-Authenticate); add the thin alias test_topbar_links_to_own_profile for the social twin scenario (C7-01)

  - Manual validation: anonymous `GET /api/posts/` → 403 with no
    `WWW-Authenticate` header; session-authenticated POST with a foreign
    JWT still acts as the session user.

## 2. web-ui scoping, policy text and gates (C8-01, C8-02, C8-03)

- [x] 2.1 Apply the web-ui delta text scoping (footer "and only on the home feed"; titles scenario scoped to the web UI) — scenarios and tests unchanged; amend the workflow GBU budget policy with the declared post-exhaustion practice
- [x] 2.2 Run the full gates: `pytest` (coverage >= 80%), `ruff check`, `ruff format --check`, `mypy`, `manage.py check`

## Workflow follow-up

- Archive after review; deltas merge into `openspec/specs/{user-accounts,web-ui}/spec.md`.
