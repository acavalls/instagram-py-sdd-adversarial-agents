# Tasks: add-stories

## 1. Models and migration (stories — Story data model)
- [ ] 1.1 Add `Story` and `StoryView` models to `apps/posts/models.py` (UUID pks, owner/story/viewer FKs, `ImageField(upload_to="stories/%Y/%m/%d/")`, `media_type` choices default image, `created_at`, `expires_at` defaulting to now + 24h on save, unique (story, viewer) constraint, indexes); tests: story persisted with placeholder media path and expiry exactly +24h (scenario: Story persisted with placeholder media)
- [ ] 1.2 Generate the migration; `makemigrations --check` clean

## 2. Service layer (stories — Story data model, Stories bar on the home page, Story view tracking, Expired story cleanup)
- [ ] 2.1 Implement `StoryService` in `apps/posts/services.py`: `create` (placeholder JPEG generation), `get_active_for_user`, `get_feed_stories` (followees only, grouped per owner, `is_viewed` per story, unviewed-first ordering), `mark_viewed` (idempotent), `is_viewed`, `cleanup_expired` (returns deleted count)
- [ ] 2.2 Tests: expired story not active anywhere (scenario: Expired story is not active); feed stories only from followed users grouped unviewed-first (scenarios: Bar lists followed users with active stories, Bar excludes non-followed users, Unviewed groups first); idempotent mark_viewed (scenario: Repeated view is idempotent); cleanup_expired deletes expired stories and reports count (scenario: Management command cleanup)

## 3. Use cases (stories — Story creation, Story view tracking)
- [ ] 3.1 `CreateStoryUseCase` and `ListFeedStoriesUseCase` in `apps/posts/use_cases.py` with the existing frozen-DTO pattern
- [ ] 3.2 `ViewStoryUseCase` enforcing self-view rejection and non-followed-story rejection (design decision 3); tests: self-view rejected with error, non-followed story not viewable (scenarios: Self-view rejected, Non-followed story not viewable)

## 4. Web layer (stories — Story creation, Stories bar on the home page, Story view tracking, Stories bar ordering; posts — Post listing MODIFIED)
- [ ] 4.1 Views `create_story`/`view_story` in `apps/web/story_views.py` + routes `/web/stories/create/` and `/web/stories/<uuid:story_id>/view/` (`@login_required`, POST-only, use-case driven, render `_toast_with_stories.html`); tests: successful web creation with toast + OOB bar (scenario: Successful web creation), unauthenticated rejected (scenario: Unauthenticated creation rejected), first view recorded with toast + OOB bar (scenario: First view recorded)
- [ ] 4.2 Templates `_stories.html` ("Your story" button + followed-user avatars with ring states) and `_toast_with_stories.html` (messages + stories bar OOB); include the bar in the feed template; tests: bar lists followed users, excludes non-followed, empty bar shows only the add button (scenarios: Bar lists followed users with active stories, Bar excludes non-followed users, Bar empty without followings)
- [ ] 4.3 Feed view calls `StoryService.cleanup_expired()` at the start and passes feed stories to the template; test: expired stories are purged on home render and removed from the bar (scenario: Lazy purge on home render)
- [ ] 4.4 Stories bar, avatar ring states and toast CSS in the stylesheet; test: ring updates after viewing (scenario: Ring updates after viewing); ordering test unviewed groups first via the rendered bar (scenario: Unviewed groups first)

## 5. Seed and management command (stories — Expired story cleanup, Story creation)
- [ ] 5.1 Extend `seed_demo_data` to create active stories for demo users (idempotent); test: seed creates stories and stays idempotent on re-run
- [ ] 5.2 Add `apps/posts/management/commands/cleanup_expired_stories.py` reporting the deleted count; test: command deletes expired stories and reports the count (scenario: Management command cleanup)

## 6. Quality gates
- [ ] 6.1 Full pytest suite green (>= 80% coverage), ruff and mypy clean
