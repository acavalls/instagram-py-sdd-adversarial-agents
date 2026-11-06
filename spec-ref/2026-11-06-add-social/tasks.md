# Tasks: add-social

## 1. Social app scaffold: Follow model
- [x] 1.1 Create `apps/social/` (apps.py, admin.py with FollowAdmin, migrations package) and register the app in `config/settings/base.py`
- [x] 1.2 Implement `Follow` model (UUID pk, follower/following FKs, created_at, unique_together, no_self_follow CheckConstraint, indexes) + migration `0001_initial` (spec: Follow relationship data)

## 2. Follow domain: service and use cases
- [x] 2.1 Implement `FollowService` (follow, unfollow, is_following, get_following, get_followers) with reference error messages (spec: Follow relationship data, Follow and unfollow actions)
- [x] 2.2 Implement `FollowUserUseCase` and `UnfollowUserUseCase` (+ exports in `use_cases/__init__.py`) (spec: Follow and unfollow actions)
- [x] 2.3 Tests: self-follow rejected, duplicate rejected, unfollow unknown, is_following, get_following/get_followers ordering (scenarios: Self-follow rejected, Duplicate follow rejected, Web follow failure shows the cause)

## 3. Feed domain: service and use cases
- [x] 3.1 Implement `FeedService` (list_feed with Follow subquery, get_suggestions excluding self/followed, -date_joined, limit 5) (spec: Followed-users feed, User suggestions)
- [x] 3.2 Implement `ListFeedUseCase` and `GetUserSuggestionsUseCase` (+ exports) (spec: Followed-users feed, User suggestions)
- [x] 3.3 Tests: feed only followed users' posts newest first, pagination window, suggestions exclude self/followed and cap at 5 (scenarios: Feed shows followed users' posts, Feed ordered newest first with pagination, Suggestions exclude followed users and self, Suggestions limited to newest accounts)

## 4. Web: followed-users home feed
- [x] 4.1 Switch `web.index` to `ListFeedUseCase` (12 per page, page param, prev/next) + empty state in `index.html` when no follows (spec: Followed-users feed)
- [x] 4.2 Suggestions panel in `index.html` sidebar via `GetUserSuggestionsUseCase` (limit 5, link to each profile) (spec: User suggestions)
- [x] 4.3 Tests: feed shows only followed users' posts, empty state, suggestions panel content (scenarios: Feed shows followed users' posts, Empty feed state, Suggestions exclude followed users and self)

## 5. Web: follow/unfollow HTMX buttons
- [x] 5.1 Views `follow_user`/`unfollow_user` (POST, login required) returning `_follow_button.html` partial with new state + success/error toast (spec: Follow and unfollow actions)
- [x] 5.2 Template `_follow_button.html` + URL routing (spec: Follow and unfollow actions)
- [x] 5.3 Tests: follow toggles state with "Followed successfully", unfollow with "Unfollowed successfully", failure keeps state with error toast (scenarios: Web follow via HTMX, Web unfollow via HTMX, Web follow failure shows the cause)

## 6. Web: profile page
- [x] 6.1 View `profile_view` (login required, 404 unknown): grid via PostService (12/page), posts/followers/following counters, is_own_profile, is_following (spec: User profile page)
- [x] 6.2 Template `profile.html` (stats row, follow button for others, post grid reusing `_post_card.html`, pagination, link to following modal) (spec: User profile page, Following list)
- [x] 6.3 Tests: own profile shows editable grid and stats, other profile shows follow state, unknown profile 404, grid pagination (scenarios: Own profile shows stats and editable grid, Other user profile shows stats and follow state, Unknown profile responds 404)

## 7. Web: following list modal
- [x] 7.1 View `following_list` (login required, 404 unknown) with `q` search (icontains username/first_name/last_name) + template `_following_list_modal.html` + routing (spec: Following list)
- [x] 7.2 Tests: list shows followed users, search filters by username and name (scenarios: Following list shows followed users, Following list search filters)

## 8. Regularization: caption limit in web update (audit F1)
- [x] 8.1 `UpdatePostUseCase` rejects caption > 2200 chars with "Caption must be 2200 characters or fewer" (spec posts: Caption length limit)
- [x] 8.2 Test: web `submit_edit` with oversized caption does not change the post and shows the error (scenario: Caption length limit)

## 9. Regularization: seed data and docs (audit F3, F6)
- [x] 9.1 `seed_demo_data` management command: demo users, follows among them, posts with generated placeholders (via services/use cases; skips if demo users exist) (spec: Followed-users feed, User profile page — enables manual validation)
- [x] 9.2 Smoke-check `/schema/?format=json` includes auth and posts paths and `/docs/` renders 200 (spec api-docs: OpenAPI documentation)
