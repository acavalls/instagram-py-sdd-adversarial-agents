# GBU Report — 2026-11-08-02-add-posts

## Cycle 1 — 2026-11-08

### Executive verdict

RECOMMENDATION: NEXT — every requirement of the three deltas (posts ADDED 7
requirements, web-ui MODIFIED sidebar + ADDED card anatomy, api-docs
MODIFIED schema) is implemented and proven by scenario-traceable tests, all
quality gates are green (273 passed / coverage 99.08% / ruff 0 / mypy 0),
the adversarial pass found and closed 5 blocking bugs across 3 attack
cycles. One honest caveat: the attack budget (calibrated 2→3) was exhausted
with the last verdict BROKEN (BUG-005); that fix is regression-verified but
received no further adversarial re-attack — the Sheriff decides at PAUSE-1.

### Requirement-by-requirement proof

| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| Post data model | Post persisted with media | Post/PostMedia with UUID ids, owner FK, ordered media (post, order), newest-first listing | apps/posts/models.py:91-105, 206-233 | test_post_persisted_with_media — passed | APPROVED (g1) |
| Post data model | Caption length limit | Field validator + save() raise, field-level error | apps/posts/models.py:19-24, 111-119 | test_caption_length_limit_on_save/_is_a_field_level_error — passed | APPROVED (g1) |
| Post data model | Bulk paths refuse over-limit captions | update()/bulk_create()/bulk_update() filter offending rows without raising | apps/posts/models.py:48-81 | test_bulk_paths_refuse_over_limit_captions_* — passed | APPROVED (g1) |
| Post data model | Non-literal caption write refused | bulk_create/bulk_update raise the model's caption validation error | apps/posts/models.py:62-76 | test_non_literal_caption_write_refused_* — passed | APPROVED (g1) |
| Post data model | Non-literal caption update refuses silently | update() returns 0 without raising | apps/posts/models.py:48-56 | test_non_literal_caption_update_refuses_silently — passed | APPROVED (g1) |
| Post data model | Legal caption bulk update applies | Legal literals write and report rows | apps/posts/models.py:65-81 | test_legal_caption_bulk_update_applies_* — passed | APPROVED (g1) |
| Post data model | Bulk paths keep the media limit | Capacity simulation on update/bulk_create/bulk_update (incl. post_id attname after BUG-003, mixed kwargs after BUG-005), rows that fit only | apps/posts/models.py:133-260 | test_bulk_paths_keep_the_media_limit_* (16+ variants) — passed | APPROVED (g1 + Bad cycles) |
| Post creation | Successful web creation | Create button posts the form; placeholder image + random caption from the app list; toast "Post created!" | apps/web/views.py:122-143; media_generator.py | test_successful_web_creation — passed | APPROVED (g4) |
| Post creation | Successful API creation | POST /api/posts/ → 201 with id/owner_username/caption/media/media_count | apps/posts/api_views.py:69-83 | test_successful_api_creation — passed | APPROVED (g3) |
| Post creation | API creation with too many media files | ListField max 10 → 400, nothing stored | apps/posts/serializers.py:28-36 | test_api_creation_with_too_many_media_files — passed | APPROVED (g3) |
| Post creation | Whitespace-only caption becomes empty | Serializer trims; empty string stored | apps/posts/serializers.py:20-27 | test_whitespace_only_caption_becomes_empty — passed | APPROVED (g3) |
| Post listing | Personal feed on the feed page | Own posts as cards, newest first, on /web/feed/ | apps/web/views.py:97-119 | test_personal_feed_on_the_feed_page — passed | APPROVED (g4) |
| Post listing | API list of own posts | GET /api/posts/ owner-filtered newest first | apps/posts/api_views.py:55-63 | test_api_list_of_own_posts — passed | APPROVED (g3) |
| Post listing | API list includes first image thumbnail | first_image_url = first image media or "" | apps/posts/serializers.py:90-101 | test_api_list_includes_first_image_thumbnail — passed | APPROVED (g3) |
| Post listing | Pagination window | limit/offset, no duplicates across pages | apps/posts/api_views.py:132-149 | test_pagination_window — passed | APPROVED (g3) |
| Post listing | Home feed loads more posts on scroll | HTMX sentinel → cards + next sentinel/end marker, no shell | post_cards.html:10-15; views.py:117-118 | test_home_feed_loads_more_posts_on_scroll — passed | APPROVED (g4) |
| Post listing | Non-HTMX request with a page parameter renders the full page | Full shell with the requested window | apps/web/views.py:106-119 | test_non_htmx_request_with_a_page_parameter_renders_the_full_page — passed | APPROVED (g4) |
| Post detail | Existing post detail | GET /api/posts/<uuid>/ → 200 with media (owner only after BUG-002) | apps/posts/api_views.py:91-99 | test_existing_post_detail — passed | APPROVED (g3 + Bad) |
| Post detail | Unknown post detail | 404 "Post not found" (non-owner treated as unknown, no existence leak) | apps/posts/use_cases/get_post.py | test_unknown_post_detail; test_other_users_post_is_reported_as_not_found — passed | APPROVED (g3 + Bad) |
| Caption update | Owner updates caption via API | PATCH → 200 updated post | apps/posts/api_views.py:105-118 | test_owner_updates_caption_via_api — passed | APPROVED (g3) |
| Caption update | Non-owner update rejected | 403 "You can only edit your own posts" (model can_edit via use case) | apps/posts/use_cases/update_post.py | test_non_owner_update_rejected — passed | APPROVED (g3) |
| Caption update | Inline web edit | Inline form updates, closes, toast "Post updated!" | apps/web/views.py:157-193 | test_inline_web_edit — passed | APPROVED (g4) |
| Caption update | Cancel inline edit | Cancel/unknown id closes without change | post_edit_form.html; views.py | test_cancel_inline_edit — passed | APPROVED (g4) |
| Post deletion | Owner deletes post via API | DELETE → 204, post and media gone | apps/posts/api_views.py:123-129 | test_owner_deletes_post_via_api — passed | APPROVED (g3) |
| Post deletion | Non-owner deletion rejected | 403 "You can only delete your own posts" | apps/posts/use_cases/delete_post.py | test_non_owner_deletion_rejected — passed | APPROVED (g3) |
| Post deletion | Web deletion removes the card | Card removed + toast "Post deleted!" | apps/web/views.py:196-217 | test_web_deletion_removes_the_card — passed | APPROVED (g4) |
| Post visibility | No cross-user listing | List/mutations owner-only; detail owner-only (BUG-002); web fragments owner-only (BUG-004) | services + use cases + views | test_no_cross_user_listing; Bad cycle regressions — passed | APPROVED (g3 + Bad) |
| Post media storage | Media stored under the post media path | upload_to="post_media/", URLs resolve; no filename overwrite (Bad verified) | apps/posts/models.py:226 | test_post_persisted_with_media; Bad storage tests — passed | APPROVED (g1 + Bad) |
| web-ui MODIFIED | Sidebar renders / placeholders (5) / logo / logout / anonymous | Create is now the POST form; Search/Explore/Messages/Notifications/Profile remain inert | apps/web/templates/web/base.html:13-66 | test_sidebar_* suite — passed | APPROVED (g4) |
| web-ui MODIFIED | Create submits the post creation form | Form POST /web/posts/create/ with CSRF | base.html:45-52 | test_create_submits_the_post_creation_form — passed | APPROVED (g4) |
| web-ui ADDED | Card anatomy (4 scenarios + own-post menu) | Avatar + username link, media or placeholder icon, inert actions row, caption + relative time, first-media-only, owner-only menu | partials/post_card.html | test_card_* suite — passed | APPROVED (g4) |
| api-docs MODIFIED | Schema serves the contract / Docs UI renders | /schema/ and /docs/ include auth AND posts paths | apps/posts/api_views.py @extend_schema; test_api_docs.py extended | test_schema_endpoint_serves_the_api_contract (extended); test_docs_ui_renders — passed | APPROVED (g3) |

### Quality gates (actual results)

pytest 273 passed, 1 xfailed (documented cycle-1 observation), 0 failed ·
coverage 99.08% (target >= 80) · ruff check: 0 issues · ruff format --check:
clean · mypy: 0 errors in 78 source files · manage.py check: no issues ·
makemigrations --check: clean · dev DB migrated (posts.0001 applied).

### Adversarial pass (The Bad)

- Cycle 1 (BROKEN):
  - 19 attacks; bulk machinery, pagination, caption boundaries, delete
    idempotency, CSRF, feed page abuse, HTMX edges, escaping, media
    generator → survived.
  - BUG-001 (HIGH): instance save() moved an existing media row into a full
    post (adding-only capacity check) → fixed (post_id-change check against
    the DB value) → regression tests in test_bad_attack_bulk_and_limits.py.
  - BUG-002 (HIGH): GET /api/posts/<uuid>/ returned other users' posts (the
    group-2 orchestrator instruction contradicted the visibility MUST; the
    spec won) → fixed (GetPostUseCase ownership check; non-owner = not
    found, no existence leak) → regression tests in
    test_bad_attack_api_abuse.py.
- Cycle 2 (BROKEN):
  - BUG-003 (HIGH): FK attname post_id on update()/bulk_update() skipped the
    capacity simulation → fixed (attname normalized to the same simulation;
    same-post rows keep their update instead of being dropped) → regression
    tests in test_bad_attack_cycle2_move_paths.py.
  - BUG-004 (HIGH): GET /web/posts/<uuid>/edit/ rendered another user's
    caption (direct get_by_id without ownership) → fixed (routed through
    GetPostUseCase; Http404 for non-owners, both branches) → regression
    tests in test_bad_attack_cycle2_edit_get.py.
- Cycle 3 (BROKEN):
  - 11 attacks; mixed-kwarg edges, boundary counts on every path, web edit
    routing, anonymous edges → survived except:
  - BUG-005 (HIGH): update(post=X, post_id=Y) mixed kwargs — simulation
    counted against the first key while SQLite last-wins stored the second →
    fixed (kwargs normalized to one canonical value before simulating;
    disagreement/non-literal → 0-row silent refusal) → regression tests in
    test_bad_attack_cycle3_mixed_kwargs.py.
  - BUDGET NOTE (honest): the attack budget was calibrated 2→3 iterations
    (documented in gbu-state.json) to complete the fix-verify loop; cycle 3
    was the last. BUG-005's fix is verified by its failing repro test now
    passing plus the full gates, but NO fourth adversarial re-attack ran.
    The Sheriff decides at PAUSE-1 whether to authorize one more attack
    cycle or accept this state.
- Non-blocking observations (MEDIUM, recorded, no fix loop): sliced-queryset
  update() raises TypeError like native Django; mixed-kwarg write target
  coincides with the simulated target only via deduplication (fragile but
  now pinned by tests); update(post_id=<malformed>) raises raw ValueError
  (spec-silent, not user-reachable); username trimming inconsistency between
  API and web adapters (carried from cycle 1, F-05).
- Budget: 8min/3runs (c1), 5min/5runs (c2), 5min/3runs (c3) — limits per
  cycle: 6 min, 6 runs; iterations: 3 calibrated (default 2, extended once,
  documented).

### Deviations and assumptions

- Post detail (GET) is owner-only: the visibility requirement's MUST
  ("other API endpoints of this capability MUST only return or mutate the
  authenticated user's own posts") was read as covering the detail GET;
  the orchestrator's initial group-2 instruction (read-any) was wrong and
  the spec won via the Bad's BUG-002.
- Card username links to /web/users/<username>/ which 404s until package 03
  delivers the profile page (declared dependency-wiring; the delta pins
  "linked to their profile page").
- Avatar is a placeholder initials div (no avatar upload exists in the
  stack); feed empty state is a simple "No posts yet" section (the old
  declared placeholder is superseded by this change's MODIFIED behavior).
- HTMX 2.0.4 enters the stack with this change (needed by the scroll
  scenarios; was declared in the fixed stack but not yet loaded).
- Mixed post/post_id disagreement refuses silently (0 rows), consistent
  with the update() contract; when they agree the canonical value is
  deduplicated so simulation and storage cannot diverge.
- Media deletion removes DB rows (FK CASCADE); disk files are not removed
  (not specified).
- PostService.list_for_user gained select_related("owner") (N+1 avoidance
  for card rendering; no behavior change).

### Manual validation pointers (mandatory when the change declares an interface)

The change declares three human-exercisable surfaces (dev server:
`.venv/bin/python manage.py runserver`):

1. Web UI:
   - Log in as `alice` (registered in cycle 1 or via /web/register/) → the
     sidebar's Create entry is now a button: click it → toast "Post
     created!" and a new card appears at the top of /web/feed/ with a
     generated placeholder image, a random caption, the actions row and
     (as owner) the edit/delete menu.
   - Create ~12 posts → scroll to the bottom of the feed → the next window
     of cards loads without reloading the page; after the last window an
     end marker appears.
   - Edit: click the edit button on one of your cards → inline form →
     change the caption → submit → toast "Post updated!" and the card
     shows the new caption; cancel an edit → nothing changes.
   - Delete: click delete on a card → the card disappears, toast "Post
     deleted!".
   - Placeholder wiring state: Search/Explore/Messages/Notifications/
     Profile remain inert links; the profile link on a card header 404s
     until package 03 (declared).
2. REST API (JWT from POST /api/auth/login/):
   - `curl -X POST :8000/api/posts/ -H "Authorization: Bearer <access>" -F "caption=hello" -F "media=@pic.png"` → 201 with media order 0;
     `-F` × 11 → 400.
   - `curl :8000/api/posts/?limit=2&offset=2` → your window, newest first,
     with first_image_url; another user's token sees only their own posts.
   - `curl -X PATCH :8000/api/posts/<uuid>/ -d '{"caption":"new"}'` → 200;
     with another user's token → 403 "You can only edit your own posts".
   - `curl -X DELETE :8000/api/posts/<uuid>/` → 204; repeat → 404 "Post not
     found".
3. API docs: open /docs/ → the posts operations (GET/POST /api/posts/,
   GET/PATCH/DELETE /api/posts/{post_id}/) now appear next to the auth
   operations; /schema/?format=json includes both path groups.

### Sheriff decision

[ ] SI — proceed to verify/archive
[ ] NO — <reason> → /opsx-update (artifacts wrong) or re-apply
