# Proposal — 04-add-stories

## Why

The app is social and navigable; stories complete the reference app's core
loop with ephemeral 24-hour content on the home page. This package ships the
stories capability end-to-end and inserts the stories bar into the feed —
the last declared dependency of the posts listing requirement.

## What Changes

- Introduce the `Story` and `StoryView` models: UUID identifiers, owner,
  image media under a dated path, creation timestamp and expiration set to
  exactly `created_at + 24h` (mismatching explicit expiry rejected);
  per-viewer view tracking with a unique (story, viewer) pair.
- Story creation from the web (`POST /web/stories/create/`) with generated
  placeholder media, success toast and an out-of-band re-render of the
  stories bar; unauthenticated requests rejected.
- Stories bar above the home feed: a "Your story" button plus one avatar
  per followed user with active stories (never non-followed users),
  unviewed groups first, ring states updating after viewing.
- Story viewing (`POST /web/stories/<uuid>/view/`) with idempotent view
  records and the declared rejection texts (self-view, non-followed
  owner, unknown/expired).
- Expired-story cleanup: lazy purge on home render plus a management
  command reporting the deleted count.

## Capabilities

### New Capabilities

- `stories`: Story data model, creation, stories bar, view tracking, bar
  ordering and expired-story cleanup.

### Modified Capabilities

- `posts`: Post listing — the stories bar is rendered above the post list
  and the home render purges expired stories (the final declared
  dependency of the listing requirement is fulfilled).

## Impact

- Models live in the `posts` app (stories are post-adjacent ephemeral
  content), services and use cases extended; new web views and templates.
- No REST endpoints (stories are web-first, matching the reference app).
- Dependencies: builds on `social` (bar shows only followed users) and the
  fixed stack (Pillow placeholder generation).
- Tests: every scenario gets a scenario-named pytest test; coverage
  >= 80%.

## Business Decisions

| Date       | Decision                                                                                                        |
| ---------- | ---------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | Stories expire exactly 24 hours after creation; an explicitly provided mismatching expiry is rejected at save.    |
| 2026-11-08 | Only followed users' stories appear in the viewer's bar and are viewable; self-views are rejected.                |
| 2026-11-08 | Rejected view attempts answer HTTP 200 with an error toast and an out-of-band bar re-render (HTMX idiom).          |
| 2026-11-08 | Bar ordering: unviewed groups first, then viewed; within a group newest first; ring state updates on re-render.    |
| 2026-11-08 | Cleanup is lazy on home render plus an on-demand management command reporting the deleted count.                   |
