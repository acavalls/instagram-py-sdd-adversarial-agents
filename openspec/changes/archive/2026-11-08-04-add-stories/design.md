# Design

## Context

The clone runs accounts, posts and social (packages 01–03): a fully
navigable social app whose feed awaits only the stories bar. This package
completes the reference app's core loop.

## Goals / Non-Goals

**Goals:**

- Ship stories end-to-end (model → service → use cases → web) closing with
  every stories scenario exercisable from the feed.
- Fulfil the posts listing requirement's last declared dependency (stories
  bar + lazy purge) via a MODIFIED delta.

**Non-Goals:**

- Video stories (media_type supports image; the reference app ships image
  placeholders).
- Story replies, highlights, notifications (sidebar placeholders remain).
- REST endpoints for stories.

## Decisions

1. **Stories live in the `posts` app** (`Story`, `StoryView` in
   `apps/posts/models.py`): they are post-adjacent ephemeral content and
   reuse the media-handling conventions; a separate app would duplicate
   the media plumbing.

2. **Expiry is a model invariant**: `save()` sets `expires_at =
   created_at + 24h` when absent and rejects an explicit mismatching
   value; `get_active_for_user`/`get_feed_stories` filter by
   `expires_at > now`. The 24-hour rule is pinned by scenarios at model
   level (folded from the original run's regularizations).

3. **View tracking with a unique (story, viewer) constraint**;
   `mark_viewed` is idempotent; `ViewStoryUseCase` enforces the rejection
   rules (self-view, non-followed owner, unknown/expired) with the exact
   toast texts.

4. **HTMX out-of-band pattern**: creation and viewing render the toast
   plus an out-of-band re-render of the stories bar (the same idiom the
   feed and follow buttons already use).

5. **Lazy purge on feed render** (cheap at clone scale) plus a management
   command for on-demand cleanup, both deleting view records with their
   stories.

## Dependency-wiring map

| Capability (this package) | Depends on | Not yet implemented? | Minimal wiring planned |
| ------------------------- | ---------- | -------------------- | ---------------------- |
| Stories bar               | Social (followed users) | No (package 03) | — |
| Bar rendering above the feed | Posts listing slot | No (declared since package 02, fulfilled here via MODIFIED delta) | — |
| "Your story" button       | None       | No | Direct creation endpoint |

## Risks / Trade-offs

- [Lazy purge on every home render could grow costly] → At clone scale the
  expired set is tiny; the management command exists for explicit cleanup.
- [Out-of-band re-renders are HTMX-magic] → Pinned by scenarios that
  assert the bar contents after creation and viewing.
- [Date-based media path] → Matches the reference app; deterministic and
  cleanup-friendly.

## Migration Plan

Additive: two new models in the `posts` app (one migration), new views/
templates/CSS. Rollback removes the migration and the bar include.

## Open Questions

None.
