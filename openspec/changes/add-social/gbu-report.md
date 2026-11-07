# GBU Report — add-social

## Cycle 1 — 2026-11-07

### Executive verdict

RECOMMENDATION: NEXT — all 9 task groups implemented and Ugly-approved on
iteration 1, the whole-change Bad attack (34 attacks) survived with zero
blocking bugs, and every quality gate is green.

### Requirement-by-requirement proof

| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| social: Follow relationship data | Follow persisted | `Follow` model with UUID pk, both FKs and `created_at` stores every relationship | apps/social/models.py:12-35 | test_follow_persisted — passed | COVERED |
| social: Follow relationship data | Self-follow rejected | DB `no_self_follow` CheckConstraint blocks the row; service raises "You cannot follow yourself" | apps/social/models.py:29-35; apps/social/services.py:12-32 | test_self_follow_rejected (model + service + use case) — passed | COVERED |
| social: Follow relationship data | Duplicate follow rejected | `unique_together` pair + service check "Already following this user" | apps/social/models.py:26; apps/social/services.py:14-35 | test_duplicate_follow_rejected (model + service + use case) — passed | COVERED |
| social: Follow and unfollow actions | Web follow via HTMX | POST view composes `FollowUserUseCase`, returns the `_follow_button.html` partial in the new state plus the "Followed successfully" toast | apps/web/social_views.py:64-96; templates/web/_follow_button.html | test_web_follow_via_htmx_toggles_to_following_with_success_toast — passed | COVERED |
| social: Follow and unfollow actions | Web unfollow via HTMX | Same flow through `UnfollowUserUseCase`, toggles back with "Unfollowed successfully" | apps/web/social_views.py:98-130 | test_web_unfollow_via_htmx_toggles_back_with_success_toast — passed | COVERED |
| social: Follow and unfollow actions | Web follow failure shows the cause | Failure re-renders the current button state with the use-case error verbatim ("You cannot follow yourself" / "Already following this user" / "Follow relationship not found") | apps/web/social_views.py:92,125 | test_web_follow_failure_* (self/duplicate/unknown) — passed | COVERED |
| social: Followed-users feed | Feed shows followed users' posts | Home composes `ListFeedUseCase` (Follow subquery, `owner__in`) — only followed users' posts render | apps/web/views.py:120-160; apps/social/services.py:86-93 | test_feed_shows_followed_users_posts_as_cards + migrated web/adversarial tests — passed | COVERED |
| social: Followed-users feed | Feed ordered newest first with pagination | Newest first with a 12-per-page page-param window, no duplicates across pages | apps/social/services.py:86-93 | test_list_feed_pagination_window_no_duplicates_across_pages; test_followed_feed_pagination_window — passed | COVERED |
| social: Followed-users feed | Empty feed state | Users who follow nobody get an empty state pointing to suggestions | apps/web/views.py:153; templates/web/feed.html:145-151 | test_empty_feed_state_when_following_nobody — passed | COVERED |
| social: User suggestions | Suggestions exclude followed users and self | `get_suggestions` excludes self + followed, `-date_joined` | apps/social/services.py:104-108 | test_get_suggestions_exclude_followed_users_and_self (domain + web) — passed | COVERED |
| social: User suggestions | Suggestions limited to newest accounts | `SUGGESTIONS_LIMIT = 5`, newest accounts first | apps/social/services.py:19,104-109 | test_get_suggestions_limited_to_five_newest_accounts (domain + web) — passed | COVERED |
| social: User profile page | Own profile shows stats and editable grid | `/web/profile/<uuid>/` with posts/followers/following counters; edit/delete controls only when `is_own_profile` | apps/web/social_views.py:165-190; templates/web/profile.html | test_own_profile_shows_stats_and_editable_grid — passed | COVERED |
| social: User profile page | Other user profile shows stats and follow state | Visitor grid plus `_follow_button.html` reflecting `is_following` | apps/web/social_views.py:178-182 | test_other_profile_shows_follow_button_for_new_visitor / ..._already_following — passed | COVERED |
| social: User profile page | Unknown profile responds 404 | `get_object_or_404`; login redirect for anonymous | apps/web/social_views.py:165 | test_unknown_profile_responds_404 — passed | COVERED |
| social: Following list | Following list shows followed users | Modal lists the profile's follows (newest relationship first), no leakage | apps/web/social_views.py:191-207; apps/social/services.py:54-71 | test_following_list_shows_followed_users — passed | COVERED |
| social: Following list | Following list search filters | Optional `q` icontains on username/first_name/last_name in the service | apps/social/services.py:54-71 | test_following_list_search_filters_by_username / _by_name — passed | COVERED |
| posts: Post listing (MODIFIED) | Personal feed on the feed page | Home shows followed users' posts; own posts remain on `GET /api/posts/` and the profile grid | apps/web/views.py:120-160 | test_feed_shows_followed_users_posts_as_cards; API tests untouched — passed | COVERED |
| posts: Post listing (MODIFIED) | API list of own posts / Pagination window | Unchanged posts API; windows without duplicates | apps/posts/ (untouched) | existing posts suite — passed | COVERED |
| posts: Post visibility (MODIFIED) | No cross-user listing | API endpoints still return/mutate only the authenticated user's own posts | apps/posts/ (untouched) | test_atk_w19 (Bad) — passed | COVERED |
| posts: Post media storage (ADDED) | Media stored under the post media path | Documents the existing `upload_to="post_media/"` convention | apps/posts/models.py:105 | existing media tests — passed | COVERED (spec-only) |
| api-docs: OpenAPI documentation | Schema endpoint serves the API contract | `/schema/?format=json` returns an OpenAPI 3.x doc with auth and posts paths | config/urls.py:24-25 | test_schema_endpoint_serves_the_api_contract — passed | COVERED |
| api-docs: OpenAPI documentation | Docs UI renders | `/docs/` renders the Swagger UI page | config/urls.py:25 | test_docs_ui_renders — passed | COVERED |
| posts: Caption length limit (regularization) | Web path pinned | Web `submit_edit` rejects > 2200 chars with the field error and the post is unchanged (guard pre-existing; test verified + scenario traceability added) | apps/web/post_views.py:175-176; apps/posts/models.py:67-73 | test_web_submit_edit_rejects_over_long_caption — passed | COVERED |

### Quality gates (actual results)

pytest 357 passed / 2 xfailed · coverage 99.48% (target >= 80) ·
ruff check: 0 issues · ruff format: 153 files clean · mypy: 0 errors in 70
source files

### Adversarial pass (The Bad)

- 34 attacks (ATK-S01..S13 domain, ATK-W01..W21 web) → all survived; 0
  blocking bugs. Regression tests committed in
  `apps/social/tests/test_bad_attacks_social.py` and
  `apps/web/tests/test_bad_attacks_social_web.py`.
- Non-blocking observations:
  - OBS-S001 (MEDIUM): following-modal `q` does not escape LIKE
    metacharacters (`%`, `_` match everything); no leak beyond followed
    users and the spec does not define literal-match semantics.
  - OBS-S002 (LOW): seed command raises CommandError if a non-demo user
    already owns a demo email (dirty DB edge).
  - OBS-S003 (LOW): `FeedService.list_feed` guards only the upper bound of
    limit/offset; negative values unreachable from views.
  - OBS-S004 (LOW): concurrent duplicate follow races to a 500 instead of
    the reference toast (DB unique constraint backstops integrity); true
    concurrency not feasible in the sandbox.
- Budget: 4 min used, 5 test runs (limits: 6 min, 6 runs, 2 iterations).

### Deviations and assumptions

- Snapshot task "F1 caption-length code fix" collapsed to test-only
  regularization: the guard already exists here (web view + `Post.save()`);
  design decision 10. (agent-decided, flagged for review)
- Media-storage delta documents this repo's real `post_media/` path instead
  of the reference's dated `post_examples/<y>/<m>/<d>/` path; design note.
  (agent-decided, flagged for review)
- `seed_demo_data` demo usernames are alphanumeric (`demoalice`…) because the
  User model's regex validator rejects underscores. (agent-decided)
- Suggestion links were placeholder `#` after group 4 and wired to real
  profile URLs in group 6, as planned.
- The 2026-11-06 audit findings CS-001/CS-002/CS-003/CS-004/TS-001/TS-002
  remain pending for a future regularization cycle (deliberately out of
  scope; ENV-001 is closed by `seed_demo_data`).

### Manual validation pointers (optional for the Sheriff)

- `python manage.py seed_demo_data`, then log in as `demoalice` /
  `demo-password-123`: home feed shows followed users' posts, suggestions
  panel links to profiles, follow/unfollow toggles with toasts.
- Visit another demo profile (`/web/profile/<uuid>/`): counters, follow
  button, following-list modal with live search.
- `/schema/?format=json` and `/docs/`.

### Sheriff decision

[ ] SI — proceed to verify/archive
[ ] NO — <reason> → /opsx-update (artifacts wrong) or re-apply
