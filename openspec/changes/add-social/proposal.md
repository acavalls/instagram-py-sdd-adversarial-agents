# Proposal

## Why

The app has no social layer: the home page shows only the logged-in user's
own posts, there is no way to follow other users, no profile pages and no
suggestions. This change adds the social capability (follows, followed-users
feed, profile pages, suggestions), replacing the personal home feed
introduced by `add-posts` as a stepping stone. It is the next step of the
roadmap (accounts → posts → social → stories → suggestions polish).

## What Changes

**New capability `social`** (mirroring the reference app's `apps/social/`):

- Follow data model: `Follow(follower, following, created_at)` with a unique
  pair constraint and a no-self-follow rule.
- Follow/unfollow behavior with reference error messages ("You cannot follow
  yourself", "Already following this user", "Follow relationship not found").
- Home feed switches from own posts to posts from followed users (newest
  first, paginated) with an empty state for users who follow nobody.
- User suggestions panel: up to 5 not-followed users, excluding self,
  newest accounts first.
- Profile page `/web/profile/<uuid>/`: post grid, posts/followers/following
  counters, own-vs-other rendering, follow button for other profiles.
- Follow/unfollow buttons via HTMX partial with toasts.
- Following list modal with search.

**Web-only decision (2026-11-05, reference parity):** the social layer is
exposed only through the web UI; no social REST endpoints are added. The
domain layer (services/use cases) stays reusable for a future social API.

**New capability `api-docs`:** living spec documenting the existing
`/schema/` (OpenAPI) and `/docs/` (Swagger UI) endpoints served by
drf-spectacular. Code already exists; this change only lands the spec.

**Regularizations absorbed in this change:**

- ENV-001 (audit 2026-11-06): `seed_demo_data` management command creating a
  demo ecosystem (users, follows, posts with generated placeholders) through
  the existing services/use cases; skips if demo users already exist.
- Caption-length web-path evidence: the web update view already rejects
  captions over 2200 characters (`apps/web/post_views.py`) and the model
  enforces the limit on every persistence path; this change adds the missing
  regression test pinning the web path (audit finding from the reference
  lineage, still untested here).

**Spec deltas on existing capabilities:**

- `posts`: MODIFIED `Post listing` and `Post visibility` (home page now shows
  the followed-users feed; own posts remain on `GET /api/posts/` and the
  owner's profile grid), ADDED `Post media storage` documenting the existing
  `post_media/` upload path convention.

**Deliberately out of scope:** stories (`add-stories`), followers list modal
(only the following list, as in the reference), notifications, real file
upload UX. The 2026-11-06 audit findings CS-001/CS-002/CS-003/CS-004/TS-001/
TS-002 stay pending for a future regularization cycle.

## Capabilities

### New Capabilities

- `social`: follows, followed-users feed, suggestions, profile pages and the
  following list modal. Owns the follow relationship and feed aggregation.
- `api-docs`: OpenAPI schema and Swagger UI exposure of the public API.

### Modified Capabilities

- `posts`: home page semantics move to the social capability (home shows the
  followed-users feed instead of own posts); media storage conventions
  documented as a new requirement.

## Impact

- New app `apps/social/` (models, services, use cases, tests).
- `apps/web/views.py`: `feed` switches from `ListPostsUseCase` to
  `ListFeedUseCase`; new views `follow_user`, `unfollow_user`, `profile_view`,
  `following_list` (likely in a new `apps/web/social_views.py`).
- `apps/posts/`: only a regression test for the existing web caption limit;
  no behavior change for the posts API.
- `config/urls.py`: no routing changes (social is web-only).
- New management command `seed_demo_data` under `apps/accounts/management/`.
- Templates: feed page gains suggestions panel and empty state; new
  `profile.html`, `_follow_button.html`, `_following_list_modal.html`.
- Home feed personal posts disappear from home (reachable via own profile).
- Database: one migration adding the `Follow` table.
