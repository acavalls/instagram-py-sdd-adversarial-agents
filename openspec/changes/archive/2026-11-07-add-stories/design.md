# Design: add-stories

## Context

Stories were an explicit non-goal of `add-social`. The reference app
implements them inside `apps/posts` (`Story`, `StoryView` models;
`StoryService`; `CreateStoryUseCase`, `ListFeedStoriesUseCase`), with two
HTMX web endpoints and lazy cleanup on the home view plus a management
command. This project already has the layered structure
(views → use cases → services → models), the HTMX web layer under `/web/`,
and the `social` capability whose `FollowService.get_following` feeds the
stories bar.

Adaptations to this repo's state (vs the reference snapshot):

- Single-module layout: `StoryService` lives in `apps/posts/services.py` and
  the use cases in `apps/posts/use_cases.py` (the reference uses packages).
- Routes under the `web` namespace: `/web/stories/create/` and
  `/web/stories/<uuid:story_id>/view/` (the reference mounts them at the
  root); the web feed view is `apps/web/views.py:feed` (name `web:feed`).
- The posts living spec's home scenario is named "Personal feed on the feed
  page" (kept in the delta; archive refuses renames).
- `seed_demo_data` already exists (add-social); stories only add a step.

## Goals / Non-Goals

- Goals: parity with the reference story behavior (create, 24h expiry, view
  tracking, grouped bar with unviewed-first ordering, lazy + command
  cleanup), implemented with this project's conventions.
- Non-Goals: real file uploads for stories (placeholder image only, same as
  posts); video media in the UI (the field allows the choice but the web
  flow always creates images); stories detail/carousel viewer (clicking an
  avatar only marks the story viewed — agent decision 2026-11-07, flagged
  for review); view counts shown to authors; notifications; DRF API
  endpoints for stories (web-only — agent decision 2026-11-07, flagged for
  review; the social layer made the same call).

## Decisions

1. **Models in `apps/posts`** (same as the reference): `Story` (UUID pk,
   owner FK, `ImageField(upload_to="stories/%Y/%m/%d/")`, `media_type` with
   image/video choices defaulting to image, `created_at`, `expires_at`),
   `StoryView` (UUID pk, story FK, viewer FK, `viewed_at`, unique constraint
   on (story, viewer), index). `Story.save` sets `expires_at` to
   `created_at + 24h` when empty (the callable `created_at` default makes the
   exact "24 hours later" scenario hold on every path). Rationale: stories
   are post-domain ephemeral media; keeps parity and migration history
   simple. Decision: agent-decided (2026-11-07).

2. **`StoryService` in `apps/posts/services.py`**, mirroring the reference
   API: `create` (generates a random-color placeholder JPEG via
   `SimpleUploadedFile`), `get_active_for_user`, `get_feed_stories` (followees
   only, grouped per owner, `is_viewed` per story, unviewed groups first),
   `mark_viewed` (idempotent `get_or_create`), `is_viewed`, `cleanup_expired`
   (returns deleted count; cascades `StoryView` via FK on_delete). Decision:
   agent-decided (2026-11-07).

3. **Deviation (flagged): `ViewStoryUseCase` added.** The reference
   `view_story` web view calls `StoryService.mark_viewed` directly, skipping
   the use-case layer. This project's convention is views → use cases →
   services, so viewing goes through a use case. The use case also enforces
   the spec rules the reference only partially enforces: reject self-view and
   reject stories from non-followed users. No new spec requirement is
   introduced by this tightening; both rules are already in the delta.
   Decision: agent-decided (2026-11-07), per the snapshot design.

4. **`CreateStoryUseCase` / `ListFeedStoriesUseCase`** follow the existing
   frozen-dataclass input/output DTO pattern used by the other use cases.

5. **Web endpoints** in `apps/web/story_views.py` (namespace `web`),
   mirroring the reference URLs under `/web/stories/`:
   `POST stories/create/` → `create_story`,
   `POST stories/<uuid:story_id>/view/` → `view_story`. Both are
   `@login_required` POST-only, call the use cases, and render
   `_toast_with_stories.html` (messages + stories bar `hx-swap-oob`
   re-render). The bar partial `_stories.html` is included by the feed
   template and by the OOB render. Decision: agent-decided (2026-11-07).

6. **Lazy purge on home render**: the feed view calls
   `StoryService.cleanup_expired()` before listing feed stories and posts
   (same as the reference). Rationale: no background workers exist in this
   project; the management command `cleanup_expired_stories` covers
   explicit/periodic runs. Decision: agent-decided (2026-11-07).

7. **CSS**: stories bar, avatar ring states (`--add`, `--viewed`,
   `--unseen`) and toast styles in the existing stylesheet, consistent with
   the current gradient/font theme. Icons via the icon set already used in
   templates.

8. **Seed**: `seed_demo_data` gains a step creating one active story for
   some demo users so the bar is populated in development (idempotent, same
   style as the existing seed). Decision: agent-decided (2026-11-07).

9. **Tests**: pytest, traceable to delta scenarios by name; factories for
   `Story`/`StoryView` following the existing test helper style. Coverage
   stays >= 80%.

## Validation boundaries

- HTTP request format at the edge (views): login requirement, POST-only
  endpoints, 404 for unknown story ids, request shaping for the HTMX partial.
- Application rules in use cases: story creation orchestration, feed stories
  retrieval, view recording with self-view and non-followed rejection, error
  mapping to the spec strings ("Story created", "Story viewed").
- Business invariants in models: `expires_at` set on save, unique
  (story, viewer) pair.
- Technical constraints in the database: unique constraint + index on
  (story, viewer), FK cascades for cleanup.

Django idiom replaces the ports + fake-adapter pattern of hexagonal
incremental flows: field validators, model save()/full_clean() and managers
act as the value objects and factories; never introduce a repository-ports
layer.

## Risks / Trade-offs

- `get_feed_stories` issues one `StoryView.exists` query per story (same as
  the reference); acceptable at demo scale, noted as future optimization.
- Self-view/non-followed rejection lives in the use case, not the DB; a
  concurrent path bypassing the use case could record such a view. Accepted:
  the unique constraint is the only DB-level guarantee, matching the
  reference.
- The lazy purge runs a DELETE on every home render; negligible at demo
  scale with the `expires_at` index.
