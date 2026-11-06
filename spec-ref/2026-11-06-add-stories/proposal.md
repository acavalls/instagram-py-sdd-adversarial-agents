# Proposal

## Why

The reference app (`/home/ale/mapfre/personal/django_ig`) implements ephemeral
stories as a core Instagram feature, but this project's living specs do not
describe them. Users currently have no way to share temporary 24-hour content
or see stories from people they follow on the home page.

## What Changes

- Add a `Story` entity with 24-hour expiry, owned by a user, with image media
  (placeholder image generated at creation, mirroring the reference app's
  no-upload behavior).
- Add a `StoryView` entity that tracks which users viewed which stories
  (unique per story/viewer pair, self-view forbidden).
- Add a `StoryService` with creation, active-stories retrieval, feed stories
  grouped by author (unviewed first), view marking, and expired-story cleanup.
- Add `CreateStoryUseCase` and `ListFeedStoriesUseCase` following the existing
  use-case layering.
- Add HTMX web endpoints `POST /stories/create/` and
  `POST /stories/<uuid:story_id>/view/` that return a toast plus an
  out-of-band re-render of the stories bar.
- Render a stories bar at the top of the home page: "Your story" add button
  plus one avatar per followed user with active stories (unviewed ring first,
  viewed ring after).
- Lazily purge expired stories when the home page is rendered, plus a
  `cleanup_expired_stories` management command for explicit cleanup.
- Seed demo stories in `seed_demo_data` so the bar is populated in
  development.

## Capabilities

### New Capabilities

- `stories`: Ephemeral 24-hour stories — creation, expiry, per-viewer view
  tracking, the home-page stories bar, and expired-story cleanup.

### Modified Capabilities

- `posts`: The home feed requirement now coexists with a stories bar above the
  post list (the post listing behavior itself is unchanged; the page structure
  gains the stories section, and expired-story purging happens on page render).

## Impact

- **Code**: new `Story`/`StoryView` models in `apps/posts/models.py`, new
  `apps/posts/services/story_service.py`, new use cases
  `create_story.py`/`list_feed_stories.py`, new web views and templates
  (`_stories.html`, `_toast_with_stories.html`), CSS additions in
  `apps/web/static/web/css/web.css`, new management command
  `cleanup_expired_stories`, update to `seed_demo_data`.
- **Migrations**: one migration adding `Story` and `StoryView` tables.
- **Specs**: new living spec `openspec/specs/stories/spec.md`; MODIFIED delta
  for `openspec/specs/posts/spec.md`.
- **Deviation from reference (flagged)**: the reference `view_story` web view
  calls `StoryService.mark_viewed` directly, bypassing the use-case layer; this
  change routes story viewing through a use case for layer consistency
  (`ViewStoryUseCase`). The reference has no `view_story.py` use case.
