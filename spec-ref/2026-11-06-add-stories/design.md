# Design

## Context

Stories were an explicit non-goal of `add-social` (its design listed them as a
future feature). The reference app implements them inside `apps/posts`
(`Story`, `StoryView` models; `StoryService`; `CreateStoryUseCase`,
`ListFeedStoriesUseCase`), with two HTMX web endpoints and lazy cleanup on the
home view plus a management command. This project already has the layered
structure (views → use cases → services → models), HTMX web layer, and the
`social` capability whose `FollowService.get_following` feeds the stories bar.

## Goals / Non-Goals

- Goals: parity with the reference story behavior (create, 24h expiry, view
  tracking, grouped bar with unviewed-first ordering, lazy + command cleanup),
  implemented with this project's conventions.
- Non-Goals: real file uploads for stories (placeholder image only, same as
  the reference); video media in the UI (the field allows the choice but the
  web flow always creates images); stories detail/carousel viewer (clicking an
  avatar only marks the story viewed, confirmed business decision); view counts
  shown to authors; notifications; DRF API endpoints for stories (web-only,
  confirmed business decision — no `/api/stories/`).

## Decisions

1. **Models in `apps/posts`** (same as the reference): `Story` (UUID pk,
   owner FK, `ImageField(upload_to="stories/%Y/%m/%d/")`, `media_type` with
   image/video choices defaulting to image, `created_at`, `expires_at`),
   `StoryView` (UUID pk, story FK, viewer FK, `viewed_at`, unique constraint
   on (story, viewer), index). `Story.save` sets `expires_at` to now + 24h
   when empty. Rationale: stories are post-domain ephemeral media; keeps
   parity and migration history simple.

2. **`StoryService` in `apps/posts/services/story_service.py`**, mirroring the
   reference API: `create` (generates a random-color placeholder JPEG via
   `SimpleUploadedFile`), `get_active_for_user`, `get_feed_stories` (followees
   only, grouped per owner, `is_viewed` per story, unviewed groups first),
   `mark_viewed` (idempotent `get_or_create`), `is_viewed`, `cleanup_expired`
   (returns deleted count; cascades `StoryView` via FK on_delete).

3. **Deviation (flagged): `ViewStoryUseCase` added.** The reference
   `view_story` web view calls `StoryService.mark_viewed` directly, skipping
   the use-case layer. This project's convention is views → use cases →
   services, so viewing goes through a use case. The use case also enforces
   the spec rules the reference only partially enforces: reject self-view and
   reject stories from non-followed users (the reference model has a `clean`
   self-view guard that the web flow never invokes). No new spec requirement
   is introduced by this tightening; both rules were already in the delta.

4. **`CreateStoryUseCase` / `ListFeedStoriesUseCase`** follow the existing
   frozen-dataclass input/output DTO pattern used by the other use cases.

5. **Web endpoints** in `apps/web/views.py` (namespace `web`), mirroring the
   reference URLs: `POST stories/create/` → `create_story`,
   `POST stories/<uuid:story_id>/view/` → `view_story`. Both are
   `@login_required`, call the use cases, and render
   `_toast_with_stories.html` (messages + stories bar `hx-swap-oob` re-render)
   targeting `#messages`. The bar partial `_stories.html` is included by
   `index.html` and by the OOB render.

6. **Lazy purge on home render**: `index` calls `StoryService.cleanup_expired()`
   before listing feed stories and posts (same as the reference). Rationale:
   no background workers exist in this project; the management command
   `cleanup_expired_stories` covers explicit/periodic runs.

7. **CSS in `web.css`**: `.stories`, `.stories__item`, `.stories__avatar`
   (+ `--add`, `--viewed`, `--unseen` ring states), `.stories__add-icon`,
   `.stories__label`, toast styles. Icons via Bootstrap Icons already used in
   templates.

8. **Seed**: `seed_demo_data` gains a step creating one active story for some
   demo users so the bar is populated in development (idempotent, same style
   as the existing seed).

9. **Tests**: pytest, traceable to delta scenarios by name (e.g.
   `test_story_persisted_with_placeholder_media`), factories for
   `Story`/`StoryView` in `apps/posts/tests/factories.py`. Coverage stays
   ≥ 80%.

## Risks / Trade-offs

- `get_feed_stories` issues one `StoryView.exists` query per story (same as
  the reference); acceptable at demo scale, noted as future optimization
  (`prefetch`/annotate).
- Self-view/non-followed rejection lives in the use case, not the DB; a
  concurrent path bypassing the use case could record such a view. Accepted:
  the unique constraint is the only DB-level guarantee, matching the
  reference.
