# spec-ref-v2 — Reformulated change sequence for the Instagram clone

This directory is the **initial specification input for a fresh clone
project**. It reformulates the original change sequence (see `spec-ref/`,
kept as the historical record) so that every change ends in a state where a
human can validate each new capability end-to-end through its declared
interface — without reading code or touching the database.

It replaces the original sequence; the regularization cycles that the
original run needed are **folded preventively** into the feature packages
below (their requirements are declared upfront, not repaired afterwards).

## Premises (why this sequence differs from the original)

1. **Exercisable-surface rule.** Every change must leave the system in a
   state where each new capability is exercisable end-to-end through the
   primary interface its delta spec declares (web UI path, API call,
   command invocation). A capability that is not exercisable is a defect.
2. **Validation-closed task groups.** Work is ordered inside-out WITHIN
   each task (domain model → service → use case → adapter), never across
   groups: adapters are not deferred to trailing groups. When a group ends,
   the capability it introduces is exercisable — and each group in
   `tasks.md` carries an explicit **Manual validation** script for the
   Sheriff.
3. **No deferred wiring.** Routes, templates, navigation entries and schema
   registration are grouped with the feature that introduces them. If the
   shell such wiring lives in does not exist yet, creating a minimal
   exercisable shell skeleton is a task of the first feature change (see
   package 01).
4. **Minimal wiring with declared placeholders.** When a capability depends
   on something not yet implemented, the plan builds the minimal wiring
   (placeholder navigation entry, stub endpoint, empty state) in the same
   change so the capability stays exercisable. Placeholders MUST be
   declared as scenarios in the delta spec; replacing one later is an
   observable change that requires its own delta (packages 02 and 03 do
   exactly this for the Create and Profile sidebar entries).
5. **Dependency-wiring map.** Each `design.md` records the external
   dependencies of every capability and the minimal wiring planned for the
   ones not yet implemented.
6. **Final-shaped specs from day one.** Requirements that the original run
   discovered late (bulk-write enforcement, POST-only logout, byte-exact
   password comparison, HTMX infinite scroll, card anatomy, profile header
   structure, secondary empty states) are part of the initial deltas here.

## Consumption order

Copy each package, in order, as the input of an OpenSpec change in the
clone repository (proposal + design + deltas + tasks are the artifacts the
propose/apply pipeline consumes; rename the directory with the clone's own
date prefix, e.g. `2026-XX-XX-01-bootstrap-accounts-shell`):

| #  | Package                        | Capabilities touched (delta type)                                        | Exercisable state after the change |
| -- | ------------------------------ | ------------------------------------------------------------------------ | ---------------------------------- |
| 01 | `01-bootstrap-accounts-shell`  | `user-accounts` (ADDED), `web-ui` (ADDED), `api-docs` (ADDED)             | Register, log in, see the app shell with placeholder navigation, log out, browse the API docs |
| 02 | `02-add-posts`                 | `posts` (ADDED), `web-ui` (MODIFIED sidebar + ADDED card anatomy), `api-docs` (MODIFIED) | Create/edit/delete posts from the sidebar and home feed, full REST surface in the schema |
| 03 | `03-add-social`                | `social` (ADDED), `posts` (MODIFIED listing), `user-accounts` (MODIFIED landing), `web-ui` (MODIFIED sidebar + ADDED profile structure) | Follow, see the followed-users feed with suggestions, visit profiles with stats and grids |
| 04 | `04-add-stories`               | `stories` (ADDED), `posts` (MODIFIED listing)                             | Create and view 24h stories from the feed's stories bar |
| 05 | `05-add-admin-console`         | `admin-console` (ADDED)                                                   | Staff manages all domain models from `/admin/` |

Run one change at a time through the full pipeline (propose → apply →
verify → archive → audit). Never batch two packages into one change: the
per-package validation scripts are only meaningful when each change closes
on an exercisable state.

## What was folded where (original → v2)

- `regularize-user-accounts-drifts` + `regularize-residual-drift` + part of
  `regularize-social-drifts` → requirements inside `01`'s `user-accounts`
  delta (bulk-write username/caption enforcement, concurrent registration
  consistency, POST-only logout, byte-exact password comparison, 401 on
  missing login fields).
- `align-web-shell` → package `01` (sidebar navigation, active state, icon
  rendering, auth layout are initial requirements, with declared
  placeholders for not-yet-implemented entries).
- `align-web-content` → folded into `02` (card anatomy, first-image
  thumbnail, whitespace caption), `03` (infinite scroll, profile header and
  tabs, suggestions column, secondary/empty states) and `04` (stories bar
  rendering expectations).
- `regularize-audit-drifts` → secondary/empty-state scenarios folded into
  `03` and `04`; the admin-console capability becomes package `05`.
- `regularize-social-drifts` (remainder) → folded into `03`'s social delta.

## Retrospective lessons encoded here

- The original run built domain-first horizontal slices and only made the
  app navigable in the sixth change (`align-web-shell`); until then the
  Sheriff could not validate features through the UI.
- Navigation and feature wiring were repeatedly repaired post-hoc by
  regularization changes; here every wiring lands with its feature and
  every placeholder is declared.
- Manual validation pointers were optional; here every task group ends
  with an executable validation script (click path / curl / command) that
  the `gbu-report.md` must carry into PAUSE-1.
