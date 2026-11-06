# Proposal

## Why

The app has identity (user-accounts, already specified) but no content: users
cannot create, view, edit or delete posts. Posts are the core entity of the
product — the social graph, the feed and stories all attach to them — so this
capability must exist before follows/feed/stories. It mirrors `apps/posts`
(Post and PostMedia only) of the reference django_ig app.

## What Changes

- Introduce the `Post` model: UUID primary key, owner (FK to user),
  optional caption (max 2200 characters), created/updated timestamps,
  owner+date and date indexes, and ownership rules (`can_edit`/`can_delete`
  restricted to the owner).
- Introduce the `PostMedia` model: UUID primary key, post FK (cascade),
  image file, media type (image/video), order; 1–10 media per post.
- Introduce post creation: caption optional, media optional (up to 10
  images); the web UI creates posts with a deterministic generated
  placeholder image (no file picker, per project principles).
- Introduce post listing: a user's own posts, newest first, limit/offset
  pagination.
- Introduce post detail, caption update and deletion, each restricted to the
  owner (403 for non-owners, 404 for unknown posts).
- Introduce the REST API surface: `GET/POST /api/posts/` and
  `GET/PATCH/DELETE /api/posts/<uuid>/`, authenticated with JWT.
- Introduce the web UI: home page shows the logged-in user's own posts
  (personal feed, replacing the placeholder), profile grid with inline
  caption edit and delete with toast feedback.
- Replace the placeholder home page ("Your feed will live here...") with the
  personal posts feed.

## Capabilities

### New Capabilities

- `posts`: Post content — post and media data model, creation (including
  placeholder media), listing, detail, caption update, deletion and
  ownership rules, exposed through the REST API and the web UI.

### Modified Capabilities

(none — `user-accounts` requirements are untouched)

## Impact

- New Django app: `posts` (models, services, use cases, serializers, API
  views) plus new views/templates in `web` (post cards, edit form, delete,
  personal feed replacing the placeholder).
- API surface: `GET/POST /api/posts/`, `GET/PATCH/DELETE /api/posts/<uuid>/`
  (200/201/204/400/403/404), JWT-authenticated.
- Config: `apps.posts` added to `INSTALLED_APPS`; `config/urls.py` gains
  `/api/posts/` and web post routes; media serving enabled in DEBUG.
- Out of scope (later changes): stories (Story/StoryView), follows, the
  followed-users feed, suggestions, other users' profile pages.

## Business Decisions

| Date       | Decision                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------- |
| 2026-11-05 | Stories (Story/StoryView) are a separate later change; this change covers Post/PostMedia only.    |
| 2026-11-05 | Web post creation uses generated placeholder images (GIF bytes), no file picker; media upload via the API accepts up to 10 images. |
| 2026-11-05 | The home page shows the user's own posts (personal feed), as in the reference Step 4.4; the followed-users feed arrives with the social change. |
| 2026-11-05 | Caption max length 2200 characters (matches reference serializer).                                |
| 2026-11-05 | Ownership errors: "You can only edit your own posts" / "You can only delete your own posts" (matches reference model rules). |
| 2026-11-05 | API status mapping: unknown post 404, non-owner 403 (both for PATCH and DELETE).                  |
| 2026-11-05 | Web CRUD flows via HTMX partials (inline edit form, delete, toasts), matching the reference Step 4.11/4.12. |
