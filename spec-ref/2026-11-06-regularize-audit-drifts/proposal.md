# Proposal: regularize-audit-drifts

## Why

The 2026-11-06 spec-audit (stage 9, run on a clean tree after archiving
add-social) found three low-severity drifts between the living specs and the
code. The spec is the source of truth, so each finding must be regularized as
an OpenSpec change instead of living as undocumented behavior.

## What Changes

- **A2 (SPEC→CODE, topbar profile link)**: the social spec's *User profile
  page* requirement is MODIFIED to document the topbar link that navigates to
  the logged-in user's own profile (added in add-social group 6).
- **A1 (SPEC→CODE, Django admin)**: a new `admin-console` capability documents
  the Django admin at `/admin/` as a staff-only management surface for
  accounts, posts and follows. This closes the decision recorded in the
  add-social design (audit finding F4) by making the exception explicit in the
  spec contract instead of leaving admin unmentioned.
- **A3 (ENVIRONMENT, config context)**: `openspec/config.yaml` context claims
  apps organized by domain "accounts, social, posts, api, web", but no `api`
  app exists (API endpoints live in `apps/accounts` and `apps/posts` with
  routing in `config/urls.py`). Fixed by editing the config context directly —
  config is project tooling, not a living spec, so no delta is needed.

## Capabilities

### New Capabilities
- `admin-console`: Django admin as an explicit staff-only management surface.

### Modified Capabilities
- `social`: *User profile page* also covers the topbar link to the own
  profile.

## Impact

- `openspec/changes/regularize-audit-drifts/` (planning artifacts only)
- `openspec/config.yaml` (context app list correction)
- Tests: one test for the topbar profile link; one smoke test for the admin
  redirect. No production code changes — all three behaviors already exist.

## Business decisions recorded

- 2026-11-06: Django admin is specified as a staff-only management surface
  (reverses the earlier "out of the spec contract" stance by making the
  exception explicit rather than silent). Source: spec-audit A1.
- 2026-11-06: the topbar profile link is desired behavior (audit A2).
