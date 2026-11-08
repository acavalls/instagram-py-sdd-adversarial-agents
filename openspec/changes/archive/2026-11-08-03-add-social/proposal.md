# Proposal — 03-add-social

## Why

Posts exist but the app is not social yet: there is no way to follow anyone,
no followed-users feed, no profiles, no discovery. This package delivers the
social capability end-to-end and switches the home feed from the declared
personal-feed stepping stone (package 02) to the real followed-users feed —
the modification that package 02's delta anticipated.

## What Changes

- Introduce the `Follow` model (UUID, follower/following, unique pair,
  no-self-follow constraint) and the follow/unfollow use cases with
  explicit error messages.
- Web follow/unfollow via an HTMX button that toggles in place with
  toasts, available on profile pages and suggestion rows.
- Switch the home feed to the followed-users feed (newest first, HTMX
  infinite scroll) with the primary empty state ("Share Photos") when the
  user follows nobody and a secondary empty state when follows have no
  posts — replacing the personal-feed interim state of package 02.
- User suggestions panel (up to 5, newest accounts, excluding self and
  followed) rendered as a right-hand column with avatar, username link,
  reason and an in-place follow button; sidebar gains the current-user
  block and the footer links.
- Profile pages at `/web/profile/<uuid>/`: posts/followers/following
  counters, HTMX infinite-scroll grid reusing the post card, follow button
  on other profiles, edit/delete controls on own posts, empty-grid
  message, header with large avatar and tabs bar (POSTS active; SAVED and
  TAGGED placeholders); the sidebar Profile placeholder is wired to the
  logged-in user's own profile.
- Following-list modal per profile, searchable by username or name.
- The authenticated landing placeholder requirement (package 01) is
  fulfilled: the landing now shows the followed-users feed.
- Web guard: editing a caption above the 2200 limit from the web keeps the
  post unchanged and reports the error.

## Capabilities

### New Capabilities

- `social`: Follow relationships, follow/unfollow actions, followed-users
  feed, user suggestions, user profile page, following list.

### Modified Capabilities

- `posts`: Post listing — the home page now shows the followed-users feed
  (the personal-feed interim state is replaced).
- `user-accounts`: Authenticated landing placeholder — fulfilled by the
  social feed.
- `web-ui`: Sidebar navigation — the Profile entry now links to the
  logged-in user's own profile; Profile page structure added.

## Impact

- New Django app: `social` (models, services, use cases) plus web views/
  templates for profiles, feed switch, suggestions, follow buttons and the
  following modal.
- No new REST endpoints (social is web-first in this clone); the posts API
  stays unchanged except for the listing semantics on the home page.
- Dependencies: builds on `posts` (grid and feed content) and `accounts`
  (users); no new dependencies.
- Tests: every scenario gets a scenario-named pytest test; coverage
  >= 80%.

## Business Decisions

| Date       | Decision                                                                                                                    |
| ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | The home feed becomes the followed-users feed in this package, replacing the declared stepping stone of package 02.           |
| 2026-11-08 | Suggestions: up to 5, newest accounts first, excluding self and already-followed; rendered in a right-hand column.            |
| 2026-11-08 | Follow/unfollow is HTMX POST-only with in-place toggle and toasts; failures keep the button state and show the cause.         |
| 2026-11-08 | Profile tabs SAVED and TAGGED are presentational placeholders (pinned by scenario), like the card actions row.                |
| 2026-11-08 | Self-follow, duplicate follow and unknown relationship rejections keep the explicit error texts of the spec.                  |
| 2026-11-08 | Following-list modal is searchable by username or name (icontains).                                                           |
