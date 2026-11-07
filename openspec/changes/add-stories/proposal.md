# Proposal

## Why

The living specs describe no ephemeral content: users cannot share temporary
24-hour media or see stories from the people they follow on the home page.
Stories are the next roadmap step (accounts → posts → social → **stories** →
suggestions polish) and build directly on the landed social capability
(`FollowService.get_following` feeds the stories bar).

## What Changes

**New capability `stories`** (mirroring the reference app's story behavior,
adapted to this repo's single-module layout):

- Data model: `Story` (UUID pk, owner FK, placeholder image media under a
  dated `stories/<year>/<month>/<day>/` path, media_type image/video default
  image, `created_at`, `expires_at` set to now + 24h on save) and `StoryView`
  (UUID pk, story FK, viewer FK, `viewed_at`, unique (story, viewer)).
- `StoryService` in `apps/posts/services.py`: `create` (generated placeholder
  image, no upload), `get_active_for_user`, `get_feed_stories` (followees
  only, grouped per owner, `is_viewed` per story, unviewed groups first),
  `mark_viewed` (idempotent), `is_viewed`, `cleanup_expired` (returns deleted
  count; view records cascade).
- Use cases `CreateStoryUseCase`, `ListFeedStoriesUseCase`, and
  `ViewStoryUseCase` in `apps/posts/use_cases.py`. **Deviation from the
  reference (flagged)**: the reference's `view_story` web view calls the
  service directly; here viewing goes through a use case that also rejects
  self-views and views of non-followed users' stories.
- Web endpoints (HTMX, session auth): `POST /web/stories/create/` and
  `POST /web/stories/<uuid:story_id>/view/` returning a toast plus an
  out-of-band re-render of the stories bar.
- Stories bar above the post list on the home page: "Your story" add button
  plus one avatar per followed user with active stories (unviewed ring
  first, viewed ring after), labeled with the username.
- Expired-story cleanup: lazy purge on home render plus a
  `cleanup_expired_stories` management command reporting the deleted count.
- `seed_demo_data` gains an idempotent step creating active stories for some
  demo users.

**Spec delta on an existing capability:**

- `posts`: MODIFIED `Post listing` (the home page renders the stories bar
  above the post list and purges expired stories before display). The post
  listing behavior itself is unchanged.

**Deliberately out of scope:** real file uploads (placeholder media only,
like posts), video in the web flow (field allows the choice; the flow always
creates images), stories detail/carousel viewer (clicking an avatar only
marks it viewed), view counts shown to authors, notifications, REST API
endpoints for stories (web-only).

## Capabilities

### New Capabilities

- `stories`: ephemeral 24-hour stories — creation, expiry, per-viewer view
  tracking, the home-page stories bar and expired-story cleanup.

### Modified Capabilities

- `posts`: the home page gains the stories bar above the post list and
  purges expired stories on render; the post listing behavior itself is
  unchanged.

## Impact

- **Code**: `Story`/`StoryView` models in `apps/posts/models.py` (+ one
  migration), `StoryService` in `apps/posts/services.py`, use cases in
  `apps/posts/use_cases.py`, web views (new `apps/web/story_views.py`),
  templates `_stories.html` / `_toast_with_stories.html` + feed template
  include, CSS additions, management command
  `apps/posts/management/commands/cleanup_expired_stories.py`, update to
  `seed_demo_data`.
- **Specs**: new living spec `openspec/specs/stories/spec.md`; MODIFIED delta
  for `openspec/specs/posts/spec.md`.
- **Deviation from reference (flagged)**: story viewing routed through a use
  case for layer consistency; the reference has no `view_story` use case.
