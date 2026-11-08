# Proposal — 02-add-posts

## Why

Users need content to publish. Posts are the foundation capability every
social feature (feed of followed users, stories, profile grids) builds on.
This package wires the full posts surface — model, REST API and web UI — in
one change, so the Sheriff can create, edit and delete posts by clicking
through the shell that package 01 delivered.

## What Changes

- Introduce the `Post` and `PostMedia` models: UUID identifiers, owner,
  caption (≤ 2200 chars) and up to 10 ordered media files; caption and
  media limits enforced on every storage path including bulk writes.
- Post creation from the web UI with generated placeholder media and a
  random caption when no file is provided; the sidebar **Create entry is
  wired** to the post creation form (replacing its placeholder link).
- The home feed page shows the logged-in user's **own posts** as post cards
  (HTMX infinite scroll; non-HTMX page parameter renders the full page).
  The followed-users feed replaces this with the social capability (package
  03) — the interim personal feed is the declared, scenario-pinned stepping
  stone.
- Full REST surface: `GET/POST /api/posts/`, `GET/PATCH/DELETE
  /api/posts/<uuid>/` with ownership rules (403 for non-owners) and
  `first_image_url` thumbnails; the OpenAPI schema gains the posts paths
  (replacing the placeholder-free api-docs state).
- Post card anatomy in the web UI (owner header, media or placeholder icon,
  presentational actions row, caption + relative time, owner edit/delete
  menu), with inline caption editing and deletion from the web.

## Capabilities

### New Capabilities

- `posts`: Post data model (with bulk-path enforcement), creation, listing,
  detail, caption update, deletion, visibility and media storage.

### Modified Capabilities

- `web-ui`: Sidebar navigation — the Create entry now submits the post
  creation form (placeholder removed); Post card anatomy added.
- `api-docs`: OpenAPI documentation — the schema now includes the posts
  paths.

## Impact

- New Django app: `posts` (models, services, use cases, serializers, API
  views) plus web views/templates for creation, feed cards, inline edit and
  deletion.
- API surface: `/api/posts/` (200/201/400), `/api/posts/<uuid>/`
  (200/204/403/404).
- Dependencies: none beyond the fixed stack (Pillow for placeholder media).
- Tests: every scenario gets a scenario-named pytest test; coverage
  >= 80%.

## Business Decisions

| Date       | Decision                                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------------ |
| 2026-11-08 | The home feed shows the user's own posts until the social capability lands (package 03 modifies it); declared, not accidental. |
| 2026-11-08 | Web creation uses generated placeholder images and a random caption (no file picker) per the fixed stack.           |
| 2026-11-08 | Caption limit (2200) and media limit (10, ordered) are enforced on every storage path including bulk writes (folded from the original run's regularizations). |
| 2026-11-08 | API captions are whitespace-trimmed; empty after trimming stores the empty string.                                  |
| 2026-11-08 | The card actions row (like/comment/share/save) is presentational placeholder UI, pinned by scenario.                |
