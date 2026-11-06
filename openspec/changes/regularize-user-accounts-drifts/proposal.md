# Proposal

## Why

The post-archive spec audit of `add-user-accounts` reported LIGHT DRIFT: 12
findings of spec-silent behavior (behavior the code has that no living spec
describes, or code that under-enforces a stated rule). The Sheriff decided
to correct the drift. This change regularizes the living spec
`user-accounts` and fixes the small code gaps so the next audit is IN SYNC.

Audit source: post-archive audit of 2026-11-06 (DRIFT-001 … DRIFT-012).

## What Changes

- Regularize into the living spec `user-accounts`:
  - The authenticated landing placeholder at `/web/feed/` (DRIFT-001).
  - The OpenAPI schema (`/schema/`) and Swagger UI (`/docs/`) surface
    (DRIFT-005).
  - JWT token lifetimes (30 min access / 1 day refresh) as observable
    contract (DRIFT-011, partial).
  - The concurrency guarantee for duplicate registration (storage-level
    uniqueness; DRIFT-008).
- Fix code so stated rules hold on every path:
  - Username alphanumeric rule enforced at the model/DB level
    (`UnicodeUsernameValidator` replaced by an alphanumeric validator), so
    admin/shell creation cannot bypass it (DRIFT-012; closes the
    DRIFT-006 concern about the admin form).
  - Logout becomes a CSRF-protected POST (Django recommendation) instead
    of a state-changing GET (DRIFT-002).
  - API login treats every failure — including blank or missing fields —
    as 401 "Invalid credentials" (DRIFT-004).
  - Passwords are never whitespace-trimmed on any path (API serializers
    stop trimming), so credentials are byte-exact across web and API
    (DRIFT-003).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `user-accounts`: ADDED requirements (API documentation surface,
  authenticated landing placeholder) and MODIFIED requirements (User
  registration, API JWT login).

## Impact

- Code: `apps/web/views.py` (logout POST), `apps/accounts/serializers.py`
  (password trim), `apps/accounts/api_views.py` (401 on blank login),
  `apps/accounts/models.py` + new migration (alphanumeric username
  validator), tests updated/added accordingly. No new dependencies.
- Spec: `openspec/specs/user-accounts/spec.md` gains 2 requirements and 2
  modified requirements after archive.
- Deliberately NOT in scope (documented, no drift to fix):
  - DRIFT-006 (admin site enabled): kept as development tooling; the
    DRIFT-012 model-level validator fix closes the bypass that made it a
    finding.
  - DRIFT-007 (media config): infrastructure for the already-specified
    optional profile picture; will be specced by the change that first
    delivers uploads.
  - DRIFT-009 (Django 6.0.10 vs "Django 5+"): satisfied — 6.0.10 meets the
    declared "5+" floor. No action.
  - DRIFT-010 (`seed_demo_data` declared but unimplemented): no living
    scenario needs it yet; it stays declared-stack future work, owned by
    the change that first requires demo data.
  - DRIFT-011 residual (tests pinning 4xx-not-500 / XSS-escaping
    invariants): Django defaults, not user-accounts requirements; left as
    tests.

## Business Decisions

| Date       | Decision                                                                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-06 | Passwords are never whitespace-trimmed on any path (agent-decided, flagged for review): byte-exact credentials beat lenient login; web path already behaved this way. |
| 2026-11-06 | Any API login failure, including blank/missing fields, answers 401 "Invalid credentials" (agent-decided, flagged for review): matches the requirement's literal "On failure … 401" wording and never leaks the cause. |
| 2026-11-06 | Logout is CSRF-protected POST-only (agent-decided, flagged for review): Django's own recommendation; the spec never mandated a method.                |
| 2026-11-06 | Admin site stays enabled as development tooling; the model-level username validator closes the rule bypass (agent-decided, flagged for review).       |
| 2026-11-06 | `seed_demo_data` remains declared-stack future work until a capability needs demo data (agent-decided, flagged for review).                            |
