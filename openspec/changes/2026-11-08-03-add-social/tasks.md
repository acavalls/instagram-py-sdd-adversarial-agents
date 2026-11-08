# Tasks

Ordering premise: inside-out WITHIN each task (model → service → use case →
adapter); each group is validation-closed, with its Manual validation line.

## 1. Social app and Follow model (Requirement: Follow relationship data)

- [ ] 1.1 Create `apps/social/` (apps.py, admin registration placeholder, migrations package) and register it in `INSTALLED_APPS`
- [ ] 1.2 Implement the `Follow` model (UUID pk, follower/following FKs, created_at, unique (follower, following) constraint, no-self-follow check constraint, indexes) + migration; tests: follow persisted with UUID and timestamp, DB rejects self-follow and duplicate pair

  - Manual validation: `manage.py makemigrations --check` clean; dev server
    boots.

## 2. Follow services and use cases (Requirements: Follow relationship data, Follow and unfollow actions)

- [ ] 2.1 Implement `FollowService` (follow, unfollow, is_following, get_following, get_followers) with the error messages "You cannot follow yourself" / "Already following this user" / "Follow relationship not found"
- [ ] 2.2 Implement `FollowUserUseCase` and `UnfollowUserUseCase`; tests: self-follow rejected, duplicate rejected, unfollow unknown, is_following, get_following ordering

  - Manual validation: run the social service/use-case tests by scenario
    name (no user-facing surface yet).

## 3. Feed and suggestion services (Requirements: Followed-users feed, User suggestions)

- [ ] 3.1 Implement `FeedService` (`list_feed` with follow subquery, newest first, limit/offset; `get_suggestions` excluding self/followed, newest accounts first, limit 5)
- [ ] 3.2 Implement `ListFeedUseCase` and `GetUserSuggestionsUseCase`; tests: feed only followed users' posts newest first, pagination window, suggestions exclude self/followed and cap at 5

  - Manual validation: run the feed/suggestion tests by scenario name.

## 4. Profile page (Requirements: User profile page; web-ui ADDED Profile page structure)

- [ ] 4.1 Implement the `profile_view` (login required, 404 unknown): grid via `PostService` (12/page), posts/followers/following counters, `is_own_profile`, `is_following`
- [ ] 4.2 Implement `profile.html`: header (large avatar, username, stats row with following-modal link, tabs bar POSTS/SAVED/TAGGED), grid wrappers with hover overlay reusing the post card, HTMX sentinel pagination, empty-grid message; tests: "Own profile shows stats and editable grid", "Other user profile shows stats and follow state", "Unknown profile responds 404", "Profile grid loads more posts on scroll", "Profile grid without posts shows an empty message", "Profile header shows avatar, stats and tabs", "Following stat opens the modal", "Grid item shows overlay"
- [ ] 4.3 Add the web-path test for the oversized-caption edit keeping the post unchanged (pins the existing "Caption length limit" scenario on the web path)

  - Manual validation: log in → Profile in the sidebar → own profile shows
    stats, tabs and the editable grid (edit/delete on own posts); visit
    another user's profile (follow button visible, no edit controls);
    an unknown profile URL responds 404.

## 5. Follow and unfollow via HTMX (Requirement: Follow and unfollow actions)

- [ ] 5.1 Implement the `follow_user`/`unfollow_user` views (POST, login required) returning the `_follow_button.html` partial with the new state plus success/error toast; wire URL routing
- [ ] 5.2 Tests: follow toggles state with "Followed successfully", unfollow with "Unfollowed successfully", failure keeps state with the error toast

  - Manual validation: on another user's profile click Follow (button
    toggles, toast "Followed successfully"); click again to unfollow;
    forcing a duplicate POST keeps the button state and shows the error.

## 6. Feed switch and landing fulfilment (Requirements: Followed-users feed; posts MODIFIED listing; user-accounts MODIFIED landing)

- [ ] 6.1 Switch `web.feed` to `ListFeedUseCase` (12 per page, HTMX sentinel, non-HTMX page parameter renders the full page) with the primary empty state ("Share Photos" icon/title/CTA) and the secondary empty state ("No posts from the people you follow yet.")
- [ ] 6.2 Tests: "Feed shows followed users' posts", "Feed ordered newest first with pagination", "Empty feed state", "Feed with follows but no posts shows the secondary empty state", "Landing requires login", "Logged-in user reaches the landing"

  - Manual validation: with two accounts (A, B): B follows A and opens the
    home page — A's posts appear newest first with infinite scroll; a
    fresh account with no follows sees the "Share Photos" empty state; an
    account following only users without posts sees the secondary message.

## 7. Suggestions panel and sidebar chrome (Requirement: User suggestions)

- [ ] 7.1 Implement `_feed_sidebar.html`: current-user block, suggestions column (avatar, username link, reason, follow button reusing `_follow_button.html`), footer links About/Help/API/Jobs/Privacy/Terms; wire into the home template
- [ ] 7.2 Tests: "Suggestions exclude followed users and self", "Suggestions limited to newest accounts", "Suggestions render as a right-hand column with follow buttons", "Suggestion follow button reflects and toggles the relationship", "Sidebar renders the current-user block and footer", "No candidates shows the empty message"

  - Manual validation: on the home page, the right column shows up to 5
    suggestions (never yourself or people you follow) with working follow
    toggles; the footer links render.

## 8. Following-list modal (Requirement: Following list)

- [ ] 8.1 Implement the `following_list` view (login required, 404 unknown) with `q` search (icontains username/first_name/last_name) + `_following_list_modal.html` + routing; tests: "Following list shows followed users", "Following list search filters"

  - Manual validation: from a profile, open the following modal via the
    following stat; type in the search box and see the list filter.

## 9. Quality gates

- [ ] 9.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green

## Workflow follow-up

- Archive the change after review; the deltas merge into
  `openspec/specs/{social,posts,user-accounts,web-ui}/spec.md`.
