# Design: regularize-audit-drifts

## Context

Stage 9 spec-audit (2026-11-06) on a clean tree reported LIGHT DRIFT with
three low-severity findings (A1 admin unmentioned, A2 topbar profile link
unspecified, A3 config context claims a non-existent `api` app). All three
behaviors already exist in code; this change makes the specs describe reality.

## Goals / Non-Goals

**Goals:**
- Living specs cover every observable surface found by the audit.
- Zero production code changes: regularization only.

**Non-Goals:**
- Specifying admin features beyond staff-only access and model management.
- Renaming or reorganizing capabilities.

## Decisions

1. **A2 via MODIFIED delta on social** (`specs/social/spec.md`): one sentence
   added to *User profile page* plus a new topbar-link scenario; the three
   existing scenarios are preserved verbatim (MODIFIED carries the whole
   requirement).

2. **A1 via new capability `admin-console`**: a single requirement keeps it
   minimal — staff-only access redirect and model management. This converts
   the add-social design's "admin out of the spec contract" stance into an
   explicit, bounded spec entry (the user accepted regularization of A1).

3. **A3 without a delta**: `openspec/config.yaml` is project tooling, not a
   living spec. The app list in its `context` is corrected directly during
   apply ("accounts, posts, social, web" — API endpoints live inside the
   domain apps with routing in `config/urls.py`).

4. **Tests added, not changed**: one test for the topbar profile link
   (social web views) and one smoke test that `/admin/` redirects anonymous
   visitors to the admin login. Traceable to the two new/changed scenarios.

## Risks / Trade-offs

- A new capability for one requirement is slightly heavy, but it keeps admin
  out of the user-facing capabilities while making its existence explicit.
- No code changes means no regression risk.
