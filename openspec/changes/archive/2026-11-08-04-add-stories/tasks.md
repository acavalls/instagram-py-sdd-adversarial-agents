# Tasks

Ordering premise: inside-out WITHIN each task (model → service → use case →
adapter); each group is validation-closed, with its Manual validation line.

## 1. Story models (Requirement: Story data model)

- [x] 1.1 Add `Story` and `StoryView` models to `apps/posts/models.py` (UUID pks, owner/story/viewer FKs, `ImageField(upload_to="stories/%Y/%m/%d/")`, `media_type` choices defaulting to image, `created_at`, `expires_at` defaulting to now + 24h on save with rejection of mismatching explicit expiry, unique (story, viewer) constraint, indexes); tests: story persisted with placeholder media path and expiry exactly +24h, mismatching explicit expiry rejected
- [x] 1.2 Generate the migration; verify `manage.py makemigrations --check` clean

  - Manual validation: migrations apply to the dev database.

## 2. Story services and use cases (Requirements: Story data model, Story view tracking, Expired story cleanup)

- [x] 2.1 Implement `StoryService` in `apps/posts/services.py`: `create` (placeholder JPEG generation), `get_active_for_user`, `get_feed_stories` (followees only, grouped per owner, `is_viewed` per story, unviewed-first ordering), `mark_viewed` (idempotent), `is_viewed`, `cleanup_expired` (returns deleted count)
- [x] 2.2 Tests: expired story not active anywhere; feed stories only from followed users grouped unviewed-first; idempotent `mark_viewed`; `cleanup_expired` deletes expired stories and reports the count
- [x] 2.3 Implement `CreateStoryUseCase`, `ListFeedStoriesUseCase` and `ViewStoryUseCase` (self-view rejection, non-followed-story rejection, unknown/expired handling) with the frozen-DTO pattern; tests: "Self-view rejected", "Non-followed story not viewable", "Unknown or expired story rejected"

  - Manual validation: run the story service/use-case tests by scenario
    name (no user-facing surface yet).

## 3. Web surface: creation, bar, viewing (Requirements: Story creation, Stories bar on the home page, Story view tracking, Stories bar ordering)

- [x] 3.1 Implement the `create_story`/`view_story` views in `apps/web/story_views.py` + routes `/web/stories/create/` and `/web/stories/<uuid:story_id>/view/` (`@login_required`, POST-only, use-case driven); tests: successful web creation with toast + out-of-band bar, unauthenticated creation rejected, first view recorded with toast + out-of-band bar
- [x] 3.2 Implement the `_stories.html` template ("Your story" button + followed-user avatars with ring states) and `_toast_with_stories.html` (messages + stories bar out-of-band); include the bar in the feed template above the post list; tests: "Bar lists followed users with active stories", "Bar excludes non-followed users", "Bar empty without followings"
- [x] 3.3 Add the stories bar, avatar ring states and toast CSS; tests: "Unviewed groups first", "Ring updates after viewing"

  - Manual validation: log in as A; as B (followed by A) create a story →
    A's home page shows B's avatar in the bar (unviewed ring); A clicks it
    ("Story viewed" toast, ring updates, group reorders); A uses the
    "Your story" button ("Story created" toast, bar refreshes out of
    band); a non-followed user's story never appears in the bar.

## 4. Expired-story cleanup (Requirement: Expired story cleanup; posts MODIFIED listing)

- [x] 4.1 Make the feed view call `StoryService.cleanup_expired()` at the start and pass the feed stories to the template (MODIFIED posts "Post listing": bar above the list, lazy purge); test: "Lazy purge on home render"
- [x] 4.2 Add `apps/posts/management/commands/cleanup_expired_stories.py` reporting the deleted count; test: "Management command cleanup"

  - Manual validation: backdate a story's `expires_at` in the shell, load
    the home page (story gone from the bar); run
    `manage.py cleanup_expired_stories` and see the deleted count.

## 5. Quality gates

- [x] 5.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green

## Workflow follow-up

- Archive the change after review; the deltas merge into
  `openspec/specs/{stories,posts}/spec.md`.
