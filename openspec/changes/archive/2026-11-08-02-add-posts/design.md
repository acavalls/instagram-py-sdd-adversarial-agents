# Design

## Context

The clone already runs the accounts capability and the exercisable shell
(package 01): a logged-in user can register, log in, see the sidebar with
placeholder entries and reach the landing page. This package fills the
posts slice end-to-end and wires the first sidebar placeholder.

## Goals / Non-Goals

**Goals:**

- Full posts slice (model → service → use cases → API + web adapters) in
  one change, closing with every posts scenario exercisable.
- Wire the sidebar Create entry and give the home feed real content.
- Card anatomy final-shaped from day one (folded from the original run's
  late `align-web-content` change).

**Non-Goals:**

- Follows, followed-users feed, suggestions, profile pages (package 03).
- Stories and the stories bar (package 04).
- Likes, comments, saves (the actions row is presentational placeholder UI
  by design).
- Media upload from the web UI (placeholder generation only).

## Decisions

1. **Clean Architecture layering as everywhere else**: `PostService` +
   five use cases (`CreatePost`, `ListPosts`, `GetPost`, `UpdatePost`,
   `DeletePost`); views stay thin; ownership rules live in the model
   (`can_edit`/`can_delete`).

2. **Bulk-path enforcement in the model layer.** Caption (≤ 2200) and
   media (≤ 10, ordered) limits are checked on save() and on queryset
   bulk operations; over-limit literal writes store nothing for the
   offending rows and non-literal values refuse the write with the model's
   validation error. This is the contract the original run had to
   regularize; it is specified upfront here.

3. **Home feed as declared stepping stone.** Until the social capability
   lands, the home feed shows the user's own posts (scenario-pinned).
   Package 03 MODIFIES this requirement to the followed-users feed. The
   card rendering, scroll sentinel and pagination mechanics are identical
   in both states, so the modification only changes the content source.

4. **Create entry wiring replaces the placeholder.** The sidebar Create
   entry becomes a form submitting `POST /web/posts/create/` — a MODIFIED
   delta on the shell requirement, not new navigation.

5. **API list includes `first_image_url`** for card thumbnails (first
   image media, empty when none), so the web cards and API consumers share
   one representation.

## Dependency-wiring map

| Capability (this package) | Depends on | Not yet implemented? | Minimal wiring planned |
| ------------------------- | ---------- | -------------------- | ---------------------- |
| Home feed cards           | Social (followed-users feed), Stories bar | Yes | Home shows the user's own posts (declared stepping stone); package 03 modifies the content source, package 04 inserts the stories bar |
| Post card edit/delete     | Profile grid | Yes (package 03) | Edit/delete controls live on the home feed cards now; the profile grid reuses the same card in package 03 |
| Card actions row          | Likes/comments/saves | Yes (out of scope) | Presentational placeholder buttons, pinned by scenario |

## Risks / Trade-offs

- [Personal-feed stepping stone could be mistaken for final state] → The
  scenario names the interim state explicitly; package 03's MODIFIED delta
  replaces it, and the audit checks the replacement happened.
- [Bulk-write validation is unusual Django code] → Pinned by dedicated
  scenarios (over-limit, non-literal, legal) at model level.
- [Placeholder media makes posts visually repetitive] → Accepted for the
  learning clone (deterministic media principle).

## Migration Plan

Additive: new `posts` app with its initial migration; template and URL
changes are additions to the existing shell. Rollback removes the app.

## Open Questions

None.
