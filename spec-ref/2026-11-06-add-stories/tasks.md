# Tasks

## 1. Models and migrations

- [x] 1.1 Add `Story` and `StoryView` models to `apps/posts/models.py` (UUID pks, owner/story/viewer FKs, `ImageField(upload_to="stories/%Y/%m/%d/")`, `media_type` choices default image, `created_at`, `expires_at` defaulting to now + 24h on save, unique (story, viewer) constraint, indexes)
- [x] 1.2 Generate and apply the migration; verify `manage.py makemigrations posts` is clean

## 2. Service layer

- [x] 2.1 Implement `apps/posts/services/story_service.py` with `create` (placeholder JPEG generation), `get_active_for_user`, `get_feed_stories` (followees only, grouped per owner, `is_viewed` per story, unviewed-first ordering), `mark_viewed` (idempotent), `is_viewed`, `cleanup_expired` (returns deleted count); export from `apps/posts/services/__init__.py`
- [x] 2.2 Add `Story`/`StoryView` factories to `apps/posts/tests/factories.py`

## 3. Use cases

- [x] 3.1 Add `create_story.py` (`CreateStoryUseCase`) and `list_feed_stories.py` (`ListFeedStoriesUseCase`) with frozen input/output dataclasses, following the existing use-case pattern; export from `apps/posts/use_cases/__init__.py`
- [x] 3.2 Add `view_story.py` (`ViewStoryUseCase`) enforcing self-view rejection and non-followed-story rejection (flagged deviation from the reference, per design decision 3)

## 4. Web layer

- [x] 4.1 Add `create_story` and `view_story` views plus URL routes `stories/create/` and `stories/<uuid:story_id>/view/` in `apps/web/views.py`/`urls.py` (`@login_required`, use-case driven, render `_toast_with_stories.html`)
- [x] 4.2 Add templates `web/_stories.html` (Your story button + followed-user avatars with ring states) and `web/_toast_with_stories.html` (messages + stories bar `hx-swap-oob`); include the bar in `web/index.html`
- [x] 4.3 Call `StoryService.cleanup_expired()` at the start of the `index` view and pass feed stories to the template
- [x] 4.4 Add stories bar, avatar ring states, and toast CSS to `apps/web/static/web/css/web.css`

## 5. Seed and management command

- [x] 5.1 Extend `seed_demo_data` to create active stories for demo users (idempotent)
- [x] 5.2 Add `apps/posts/management/commands/cleanup_expired_stories.py` reporting the deleted count

## 6. Tests

- [x] 6.1 Model tests: placeholder media creation, 24h expiry set on save, expired story not active (`test_story_persisted_with_placeholder_media`, `test_expired_story_is_not_active`)
- [x] 6.2 Creation tests: successful web creation with toast + OOB bar, unauthenticated rejected
- [x] 6.3 Stories bar tests: followed users listed, non-followed excluded, empty bar with only the add button
- [x] 6.4 View tracking tests: first view recorded, repeated view idempotent, self-view rejected, non-followed story not viewable
- [x] 6.5 Ordering tests: unviewed groups first, ring updates after viewing
- [x] 6.6 Cleanup tests: lazy purge on home render, management command deletes expired stories and reports count

## 7. Quality gates

- [x] 7.1 Run full pytest suite (all tests pass, previous 124 preserved) and coverage (≥ 80%)
- [x] 7.2 Run ruff and mypy clean
- [x] 7.3 Manual smoke: `seed_demo_data`, log in as a demo user, create a story, view a followed user's story, verify bar ordering and toasts

## Workflow follow-up

- Commit implementation (user performs the commit at the gate)
- Verify the change (`/opsx-verify`)
- Archive the change (`/opsx-archive`)
