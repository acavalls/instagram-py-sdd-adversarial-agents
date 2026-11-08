# Design

## Context

The clone runs accounts (package 01) and posts (package 02): users can log
in, see the shell and publish posts shown on their personal home feed. This
package makes the app social and fulfils the two declared placeholders that
refer to it (the landing content and the sidebar Profile entry).

## Goals / Non-Goals

**Goals:**

- Ship the whole social slice (follow, feed, suggestions, profiles,
  following modal) closing on a fully navigable social app.
- Replace the declared personal-feed stepping stone with the followed-users
  feed through a MODIFIED delta, not a silent switch.
- Final-shaped UI from day one (infinite scroll, profile header/tabs,
  suggestions column, secondary empty states — folded from the original
  run's late `align-web-content` change).

**Non-Goals:**

- Stories and the stories bar (package 04).
- Followers list (only the following list ships, matching the reference
  app).
- Private profiles, block/mute, DMs, notifications (sidebar placeholders
  remain).

## Decisions

1. **Follow model with hard constraints**: unique (follower, following)
   pair and a no-self-follow check constraint at the database level;
   services add the friendly error messages.

2. **Feed aggregation in `FeedService`**: followed-users posts newest
   first with a follow subquery; suggestions exclude self/followed,
   newest accounts first, capped at 5.

3. **One follow button partial** (`_follow_button.html`) reused by the
   profile page and the suggestions rows; HTMX POST endpoints with
   login_required; failures re-render the button in place with an error
   toast.

4. **Profile grid reuses the post card** (package 02's anatomy) inside
   grid wrappers with a hover overlay; edit/delete controls appear on the
   owner's own grid items; the grid paginates through an HTMX sentinel
   like the feed.

5. **Landing requirement fulfilled via MODIFIED delta**: the
   user-accounts landing placeholder loses its placeholder scenario and
   points to the social capability; the posts listing requirement changes
   its home-page content source. Both modifications are declared in this
   package, keeping the spec graph honest.

6. **Web caption guard**: the oversized-caption edit is rejected on the
   web path too, keeping the post unchanged and reporting the error —
   the same limit enforced by the model and the API.

## Dependency-wiring map

| Capability (this package) | Depends on | Not yet implemented? | Minimal wiring planned |
| ------------------------- | ---------- | -------------------- | ---------------------- |
| Followed-users feed       | Posts (content) | No (package 02) | — |
| Stories bar above the feed | Stories | Yes (package 04) | The feed renders without the bar; package 04 inserts it via a MODIFIED listing delta |
| Profile grid              | Posts (cards) | No (package 02) | — |
| Search/Explore/Messages/Notifications sidebar entries | Future capabilities | Yes (out of this sequence's scope unless added later) | They remain declared placeholder links, pinned by scenario |

## Risks / Trade-offs

- [Follow subquery feed performance] → Irrelevant at clone scale; indexed
  FKs and `select_related` keep it simple.
- [Two empty states could confuse] → Both are scenario-pinned with
  distinct messages and triggers (no follows vs. follows without posts).
- [MODIFIED deltas across three capabilities] → The package touches
  posts/user-accounts/web-ui deltas in one coordinated change so the
  switch is atomic; verify checks all three.

## Migration Plan

Additive: new `social` app with its initial migration; the feed switch and
sidebar wiring are template/view changes over existing surfaces. Rollback
removes the app and reverts the two view changes.

## Open Questions

None.
