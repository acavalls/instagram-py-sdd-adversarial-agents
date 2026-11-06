# Proposal: regularize-audit-drifts-3

## Why

Audit #6 (post `align-web-content`) reported LIGHT DRIFT with 8 low findings:
observable UI states with no spec coverage (F1-F3, F6), a spec-vs-design
disagreement about non-HTMX pagination (F4), a test gap (F5), a config
wording mismatch (F7) and missing scenario traceability on supplementary
tests (F8).

## What Changes

- `social` / Followed-users feed: ADD scenario for the secondary empty state
  (follows exist but no followed posts) — F1.
- `social` / User profile page: ADD scenario for the empty profile grid — F2.
- `social` / User suggestions: name the panel chrome (current-user block,
  footer links) and ADD scenario for the no-candidates message — F3.
- `posts` / Post listing and `social` / User profile page: document that
  non-HTMX GETs honor `?page=` by rendering the full page at that window — F4
  (chosen: update spec, keep code; progressive-enhancement behavior).
- `web-ui` / Post card anatomy and Profile page structure: state that a post
  with multiple media renders only the first media file — F6 (chosen: update
  spec, matches reference parity; a carousel would need a new change).
- Test fixes: assert the empty-feed icon (F5); add scenario docstrings to 4
  supplementary tests (F8).
- `openspec/config.yaml`: `seed_data` → `seed_demo_data` — F7.

## Impact

- Affected specs: `social` (3 MODIFIED), `posts` (1 MODIFIED), `web-ui`
  (2 MODIFIED).
- Affected code: none (spec-side regularization). Tests only (F5, F8).
- Risk: none.
