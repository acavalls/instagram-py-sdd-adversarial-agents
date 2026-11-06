# Proposal: add-social

## Why

The app currently has no social layer: the home page shows only the logged-in
user's own posts, there is no way to follow other users, no profile pages and
no suggestions. This change adds the social capability (follows, followed-users
feed, profile pages, suggestions), replacing the personal home feed introduced
by `add-posts` as a stepping stone. It is the third change in the roadmap
(accounts → posts → social → stories → suggestions polish).

It also absorbs the low-severity drift findings from the spec-audit run of
2026-11-05 (F1–F6), which the user decided to fold into this change.

## What Changes

**New capability `social`** (mirroring the reference app `apps/social/`):

- Follow data model: `Follow(follower, following, created_at)` with unique
  pair constraint and no-self-follow rule.
- Follow/unfollow behavior with reference error messages.
- Home feed switches from own posts to posts from followed users (newest
  first, paginated) with an empty state for new users.
- User suggestions panel: up to 5 not-followed users, newest accounts first.
- Profile page `/web/profile/<uuid>/`: post grid, posts/followers/following
  counters, own-vs-other rendering, follow button.
- Follow/unfollow buttons via HTMX partial with toasts.
- Following list modal with search.

**Web-only decision (2026-11-05):** like the reference app, the social layer
is exposed only through the web UI; no social REST endpoints are added.

**Absorbed audit regularizations:**

- F1 (CODE→SPEC): enforce the 2200-character caption limit in the web update
  path via `UpdatePostUseCase` (code fix; spec already requires it).
- F2 (SEMANTIC): resolved by this change itself — "profile grid" becomes real;
  edit/delete interactions move to the profile grid (own posts no longer
  appear on home).
- F3 (SPEC→CODE): new `api-docs` capability spec describing `/schema/` and
  `/docs/`.
- F4 (SPEC→CODE): business decision recorded — Django admin stays out of the
  spec contract on purpose.
- F5 (SPEC→CODE): ADDED requirement in the posts spec documenting media
  storage conventions.
- F6 (ENVIRONMENT): `seed_demo_data` management command so the config context
  claim ("seed_data management commands") becomes true; it also eases manual
  validation of the feed.

**Spec deltas on existing capabilities:**

- `posts`: MODIFIED `Post listing` and `Post visibility` (home page now shows
  the followed-users feed; own posts remain on `GET /api/posts/` and the
  owner's profile grid), ADDED `Post media storage`.
- `api-docs`: new capability with one requirement (OpenAPI schema + Swagger UI).

## Capabilities

### New Capabilities

- `social`: follows, followed-users feed, suggestions, profile pages.
- `api-docs`: OpenAPI schema and Swagger UI exposure.

### Modified Capabilities

- `posts`: home page semantics move to the social capability; media storage
  conventions documented.

## Impact

- New app `apps/social/` (models, services, use cases, tests).
- `apps/web/views.py`: `index` switches to `ListFeedUseCase`; new views
  `follow_user`, `unfollow_user`, `profile_view`, `following_list`.
- `apps/posts/`: small fix in `UpdatePostUseCase` (caption length); no
  behavior change for the posts API.
- `config/urls.py`: no routing changes (social is web-only).
- New management command `seed_demo_data`.
- Templates: `index.html` gains suggestions panel and empty state; new
  `profile.html`, `_follow_button.html`, `_following_list_modal.html`.
- Home feed personal posts disappear from home (reachable via own profile).
