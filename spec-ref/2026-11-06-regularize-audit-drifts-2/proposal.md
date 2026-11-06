# Proposal

## Why

Audit #3 (2026-11-06) reported four low-severity drifts between the living
specs and the code after `add-stories`: an expired story can still be viewed
(C1), the "Story not found" toast is undescribed behavior (C2), the stories
spec writes URLs without the `/web` prefix used by the rest of the specs (S1),
and the admin-console scenario "Staff manages domain models" still has no test
(T1, carried over from audit #2).

## What Changes

- **C1 (fix code)**: `ViewStoryUseCase` rejects stories whose expiration
  timestamp has passed ("Story has expired"), matching the spec's "active
  story" wording; new test for the use case and the web view.
- **C2 (update spec)**: document the "Story not found" toast as a new scenario
  under the "Story view tracking" requirement (the existing
  `test_unknown_story_rejected` test becomes traceable by that scenario name).
- **S1 (update spec)**: rewrite stories-spec endpoint URLs to the `/web/`
  prefix convention (`/web/stories/create/`, `/web/stories/<uuid>/view/`)
  used by the other living specs.
- **T1 (fix code)**: add a staff-user test asserting the `/admin/` changelists
  for User, Post, Follow and Story, traceable to the existing admin-console
  scenario.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `stories`: "Story creation" and "Story view tracking" gain the `/web/` URL
  prefix (S1); "Story view tracking" gains an "Unknown story reported as not
  found" scenario (C2). No behavior changes beyond the already-specified ones.

## Impact

- **Code**: `apps/posts/use_cases/view_story.py` (expiry check), tests in
  `apps/posts/tests/` (expired-story rejection, scenario-name traceability)
  and `apps/accounts/tests/` (admin changelist test).
- **Specs**: MODIFIED delta for `openspec/specs/stories/spec.md` only.
- No migrations, no new dependencies, no new endpoints.
