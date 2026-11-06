# Design

## Context

The project has the accounts capability (living spec `user-accounts`) with
the established layering: views → use_cases → services → models, apps
organized by domain (`apps.accounts`, `apps.web`). The web feed page is a
login-required placeholder (`apps/web/views.py:feed`). This change adds the
`posts` domain: Post/PostMedia only (stories are a later change). See
proposal.md for motivation and the delta specs for requirements.

## Goals / Non-Goals

**Goals:**

- Mirror the reference posts slice: model + service + use cases + API
  serializers/views + web HTMX CRUD.
- Keep every scenario in the delta specs covered by a scenario-named test.
- Wire media serving in DEBUG so placeholder images render.

**Non-Goals:**

- Story/StoryView models (later change).
- Follows, followed-users feed, suggestions, other users' profile pages.
- Real file upload from the web UI (placeholder generation only).

## Decisions

1. **Models mirror the reference, minus stories.** `Post` (UUID PK, owner FK
   with `related_name="posts"`, caption blank/default "", max 2200,
   `ordering = ["-created_at"]`, indexes `(owner, -created_at)` and
   `(-created_at)`, `can_edit`/`can_delete` returning `(bool, error)`) and
   `PostMedia` (post FK cascade, `ImageField`, `MediaType` choices
   image/video, zero-based `order`, index `(post, order)`).
   Alternative: separate media table keyed by URL — rejected, more code with
   no benefit for a learning clone.

2. **Ownership rules live on the model** (`can_edit`/`can_delete` with the
   spec error messages), consumed by use cases. Use cases translate them
   into success/error outputs; API views map errors to 403 (message contains
   "own") or 404 ("Post not found"). Alternative: ownership checks in views —
   rejected, violates layer discipline (config.yaml principle 3).

3. **Service layer**: `PostService.get_by_id` (with
   `select_related("owner").prefetch_related("media")`), `list_for_user`
   (filter by owner, newest first, limit/offset), `exists`, `is_owner`,
   `create` (post + `bulk_create` of media), `update_caption`
   (`update_fields=["caption", "updated_at"]`), `delete`.

4. **Placeholder generation in the web layer, not the domain**: the web view
   builds a 1x1 GIF (`SimpleUploadedFile`) with a random color filename and
   a random caption from a fixed caption list. The use case receives the file
   like any other media. Alternative: generating placeholders inside
   `PostService.create` — rejected, couples the domain to UI concerns.

5. **API surface**: `PostListCreateView` (GET with limit/offset, POST with
   create serializer: caption ≤2200, media `ListField` max 10) and
   `PostDetailView` (GET/PATCH/DELETE; PATCH requires caption). Read
   serializers: `PostReadSerializer` (nested media + `media_count`) and
   `PostListSerializer` (with `first_image_url`). Unknown post → 404 with
   "Post not found"; non-owner PATCH/DELETE → 403 with the model's ownership
   error message.

6. **Web CRUD via HTMX partials**: `POST /web/posts/create/` (placeholder
   post + redirect + toast), inline edit form (`GET .../edit-form/`,
   `GET .../cancel-edit/`, `POST .../submit-edit/`), delete
   (`POST .../delete/`), all `@login_required`, toasts through the messages
   framework. The feed view (`apps/web/views.py:feed`) switches from the
   placeholder paragraph to the user's own posts (paginated).

7. **HTMX adoption**: add the htmx script to `base.html` (CDN). No new
   Python dependency.

8. **Tests per scenario, named after it**, following the established suite
   layout: `apps/posts/tests/` (models, services, use cases, api views) and
   `apps/web/tests/test_post_views.py` for the web CRUD flows, with
   post/media factories producing GIF bytes.

## Risks / Trade-offs

- [Placeholder GIF named `.jpg`] → cosmetic; renders fine in browsers;
  a future change may fix the extension.
- [Personal feed on `/web/feed/` will be replaced by the followed-users
  feed] → intentional stepping stone; the social change will modify it via
  a delta.
- [Media files accumulate in `media/` during tests] → accepted for a
  learning clone; cleanup is out of scope.

## Migration Plan

Additive: new app + migration (`0001_initial` for Post/PostMedia), new URLs.
Rollback is trivial. Apply `migrate` after generating migrations (lesson
from add-user-accounts validation).

## Open Questions

None.
