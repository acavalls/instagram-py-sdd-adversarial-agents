# Tasks: add-social

## 1. Social app scaffold: Follow model (spec: social — Follow relationship data)
- [ ] 1.1 Create `apps/social/` (apps.py, admin.py with FollowAdmin, migrations package, empty services.py and use_cases.py) and register the app in `config/settings/base.py`
- [ ] 1.2 Implement `Follow` model (UUID pk, follower/following FKs, created_at, unique_together, no_self_follow CheckConstraint, indexes) + migration `0001_initial`; tests: follow persisted with UUID and timestamp, DB rejects self-follow and duplicate pair (scenarios: Follow persisted, Self-follow rejected, Duplicate follow rejected)

## 2. Follow domain: service and use cases (spec: social — Follow relationship data, Follow and unfollow actions)
- [ ] 2.1 Implement `FollowService` (follow, unfollow, is_following, get_following, get_followers) with reference error messages "You cannot follow yourself" / "Already following this user" / "Follow relationship not found"
- [ ] 2.2 Implement `FollowUserUseCase` and `UnfollowUserUseCase` (exports in `apps/social/use_cases.py`)
- [ ] 2.3 Tests: self-follow rejected, duplicate rejected, unfollow unknown, is_following, get_following/get_followers ordering (scenarios: Self-follow rejected, Duplicate follow rejected, Web follow failure shows the cause)

## 3. Feed domain: service and use cases (spec: social — Followed-users feed, User suggestions)
- [ ] 3.1 Implement `FeedService` (list_feed with Follow subquery, get_suggestions excluding self/followed, -date_joined, limit 5)
- [ ] 3.2 Implement `ListFeedUseCase` and `GetUserSuggestionsUseCase` (exports in `apps/social/use_cases.py`)
- [ ] 3.3 Tests: feed only followed users' posts newest first, pagination window, suggestions exclude self/followed and cap at 5 (scenarios: Feed shows followed users' posts, Feed ordered newest first with pagination, Suggestions exclude followed users and self, Suggestions limited to newest accounts)

## 4. Web: followed-users home feed (spec: social — Followed-users feed, User suggestions; posts — Post listing MODIFIED)
- [ ] 4.1 Switch `web.feed` to `ListFeedUseCase` (12 per page, page param, prev/next) + empty state in the feed template when the user follows nobody
- [ ] 4.2 Suggestions panel in the feed template sidebar via `GetUserSuggestionsUseCase` (limit 5, link to each profile)
- [ ] 4.3 Tests: feed shows only followed users' posts, empty state, suggestions panel content (scenarios: Feed shows followed users' posts, Empty feed state, Suggestions exclude followed users and self)

## 5. Web: follow/unfollow HTMX buttons (spec: social — Follow and unfollow actions)
- [ ] 5.1 Views `follow_user`/`unfollow_user` (POST, login required) returning the `_follow_button.html` partial with the new state + success/error toast
- [ ] 5.2 Template `_follow_button.html` + URL routing
- [ ] 5.3 Tests: follow toggles state with "Followed successfully", unfollow with "Unfollowed successfully", failure keeps state with error toast (scenarios: Web follow via HTMX, Web unfollow via HTMX, Web follow failure shows the cause)

## 6. Web: profile page (spec: social — User profile page)
- [ ] 6.1 View `profile_view` (login required, 404 unknown): grid via PostService (12/page), posts/followers/following counters, is_own_profile, is_following
- [ ] 6.2 Template `profile.html` (stats row, follow button for others, post grid reusing the existing post card, pagination, link to following modal)
- [ ] 6.3 Tests: own profile shows editable grid and stats, other profile shows follow state, unknown profile 404, grid pagination (scenarios: Own profile shows stats and editable grid, Other user profile shows stats and follow state, Unknown profile responds 404)

## 7. Web: following list modal (spec: social — Following list)
- [ ] 7.1 View `following_list` (login required, 404 unknown) with `q` search (icontains username/first_name/last_name) + template `_following_list_modal.html` + routing
- [ ] 7.2 Tests: list shows followed users, search filters by username and name (scenarios: Following list shows followed users, Following list search filters)

## 8. Regularization: web caption-limit regression test (posts — Caption length limit)
- [ ] 8.1 Test: web `submit_edit` with an oversized caption (> 2200) does not change the post and reports the error (scenario: Caption length limit)

## 9. Regularization: seed data and api-docs tests (social — Followed-users feed, User profile page; api-docs — OpenAPI documentation)
- [ ] 9.1 `seed_demo_data` management command: demo users, follows among them, posts with generated placeholders (via services/use cases; skips if demo users exist); test: command creates the ecosystem and is idempotent on re-run
- [ ] 9.2 Tests: `/schema/?format=json` includes auth and posts paths and `/docs/` renders 200 (scenarios: Schema endpoint serves the API contract, Docs UI renders)
