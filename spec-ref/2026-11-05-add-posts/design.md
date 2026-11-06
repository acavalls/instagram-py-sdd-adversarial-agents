# Design

## Context

The project has the scaffold plus the `user-accounts` capability (archived).
The reference implementation lives in `/home/ale/mapfre/personal/django_ig`
(`apps/posts` — Post/PostMedia/Story/StoryView — and the post views in
`apps/web`). See proposal.md for motivation. This design covers only
Post/PostMedia; stories are a later change.

## Goals / Non-Goals

**Goals:**

- Mirror the reference posts slice: model + service + use cases + API
  serializers/views + web HTMX CRUD.
- Keep every scenario in the delta spec covered by a scenario-named test.
- Wire media serving in DEBUG so placeholder images render.

**Non-Goals:**

- Story/StoryView models (later change).
- Follows, followed-users feed, suggestions, other users' profile pages.
- Real file upload from the web UI (placeholder generation only).

## Decisions

1. **Models copied from the reference, minus stories.** `Post` (UUID PK,
   owner FK with `related_name="posts"`, caption blank/default "",
   `ordering = ["-created_at"]`, indexes `(owner, -created_at)` and
   `(-created_at)`, `can_edit`/`can_delete` returning `(bool, error)`) and
   `PostMedia` (post FK cascade, `ImageField`, `MediaType` choices
   image/video, zero-based `order`, index `(post, order)`).
   Alternative: separate media table keyed by URL — rejected, no parity and
   more code.

2. **Ownership rules live on the model** (`can_edit`/`can_delete`), consumed
   by use cases — exactly as the reference (Step 4.10 "Domain Invariants in
   Models"). Use cases translate them into success/error outputs; API views
   map errors to 403 (contains "own") or 404.

3. **Service layer as in the reference**: `PostService.get_by_id` (with
   `select_related("owner").prefetch_related("media")`), `list_for_user`
   (filter by owner, newest first, limit/offset), `exists`, `is_owner`,
   `create` (post + `bulk_create` of media), `update_caption`
   (`update_fields=["caption", "updated_at"]`), `delete`.

4. **Placeholder generation in the web layer**, not the domain: the web view
   builds a 1x1 GIF (`SimpleUploadedFile`) with a random color filename and a
   random caption from a fixed list — mirroring the reference
   `create_random_post`. The use case receives the file like any other media.
   Alternative: generating placeholders in `PostService.create` — rejected,
   it would couple the domain to UI concerns.

5. **API surface identical to the reference**: `PostListCreateView` (GET with
   limit/offset, POST with `PostCreateSerializer`: caption ≤2200, media
   `ListField(ImageField, max_length=10)`) and `PostDetailView`
   (GET/PATCH/DELETE; PATCH requires caption). Read serializers mirror the
   reference (`PostReadSerializer` with nested media + `media_count`;
   `PostListSerializer` with `first_image_url`).

6. **Web CRUD via HTMX partials** as in the reference Step 4.11/4.12:
   `POST /web/posts/create/` (placeholder post + redirect + toast), inline
   edit form (`GET .../edit-form/`, `GET .../cancel-edit/`,
   `POST .../submit-edit/`), delete (`POST .../delete/`), all
   `@login_required` and posting toasts through the messages framework.
   The home page (`index`) switches from the placeholder to the user's own
   posts (paginated).

7. **HTMX adoption**: add the htmx script to `base.html` (CDN) — this is the
   change that first uses it, resolving the ENVIRONMENT drift finding from
   the spec-audit. No new Python dependency.

8. **Tests per scenario, named after it**, following the established suite
   layout: `apps/posts/tests/` (models, services, use cases, api views) and
   web CRUD tests in `apps/accounts/tests/test_web_views.py`'s sibling
   `apps/posts/tests/test_web_views.py`, with `PostFactory`/`PostMediaFactory`
   (GIF bytes) as in the reference.

## Risks / Trade-offs

- [Placeholder GIF named `.jpg`] → cosmetic; matches the reference and
  renders fine; a future change may fix the extension.
- [Personal feed on `/web/` will be replaced by the followed-users feed] →
  intentional stepping stone (reference Step 4.4); the social change will
  modify it via a delta.
- [Media files accumulate in `media/` during tests] → accepted for a
  learning clone; cleanup is out of scope.

## Migration Plan

Additive: new app + migration (`0001_initial` for Post/PostMedia), new URLs.
Rollback is trivial. Apply `migrate` after generating migrations (lesson from
add-user-accounts validation).

## Open Questions

None.
