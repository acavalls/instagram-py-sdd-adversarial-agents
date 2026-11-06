# GBU Report — add-posts

## Cycle 1 — 2026-11-06

### Executive verdict
RECOMMENDATION: NEXT — the implementation satisfies every delta-spec scenario with
scenario-named tests, survived the full adversarial pass after two HIGH bugs were
found and fixed, and all quality gates are green (coverage 99.42%).

### Requirement-by-requirement proof
| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| Post data model | Post persisted with media | Posts get UUID ids; media rows keep a zero-based order; listings order newest first | apps/posts/models.py:39-58, 97-121 | test_post_persisted_with_media (pass) | APPROVED |
| Post data model | Caption length limit | Caption field max 2200; enforced by the field validator, by full_clean and by Post.save on every persistence path | apps/posts/models.py:63-72 | test_caption_length_limit (pass) | APPROVED |
| Post creation | Successful web creation | The web layer builds a 1x1 GIF placeholder and picks a random caption from a fixed list, then the CreatePost use case persists it; toast "Post created!" | apps/web/post_views.py:44-80, 107-124 | test_successful_web_creation (pass) | APPROVED |
| Post creation | Successful API creation | POST /api/posts/ with caption + media runs CreatePostUseCase; 201 with id, owner_username, caption, media, media_count | apps/posts/api_views.py (PostListCreateView) | test_successful_api_creation (pass) | APPROVED |
| Post creation | API creation with too many media files | ListField max_length=10 rejects 11+ files with a 400 field error before persisting anything | apps/posts/serializers.py:84-89 | test_api_creation_with_too_many_media_files (pass) | APPROVED |
| Post listing | Personal feed on the feed page | The feed view lists the user's own posts via ListPostsUseCase and renders post cards (media, caption, owner, timestamp) | apps/web/views.py:120-142; apps/web/templates/web/feed.html | test_personal_feed_on_the_feed_page (pass) | APPROVED |
| Post listing | API list of own posts | GET /api/posts/ returns only the authenticated user's posts, newest first, with limit/offset | apps/posts/api_views.py | test_api_list_of_own_posts (pass) | APPROVED |
| Post listing | Pagination window | Service slices [offset:offset+limit]; disjoint windows asserted; unbounded integers clamped at the DB bound | apps/posts/services.py:28-37 | test_pagination_window (pass); test_atk005b/test_ratk004 (pass) | APPROVED |
| Post detail | Existing post detail | GET /api/posts/<uuid>/ returns the post with nested media | apps/posts/api_views.py (PostDetailView) | test_existing_post_detail (pass) | APPROVED |
| Post detail | Unknown post detail | Unknown or non-owned id answers 404 {"error": "Post not found"} (ownership folded into GetPost after the adversarial pass) | apps/posts/use_cases.py (GetPostUseCase) | test_unknown_post_detail (pass); test_atk001 (pass) | APPROVED |
| Caption update | Owner updates caption via API | PATCH /api/posts/<uuid>/ updates the caption (update_fields=["caption","updated_at"]) | apps/posts/services.py:76-80 | test_owner_updates_caption_via_api (pass) | APPROVED |
| Caption update | Non-owner update rejected | Use case consumes Post.can_edit; 403 with the exact text "You can only edit your own posts" | apps/posts/use_cases.py:153-155 | test_non_owner_update_rejected (pass) | APPROVED |
| Caption update | Inline web edit | HTMX edit-form/submit-edit endpoints swap the card partial; toast "Post updated!" | apps/web/post_views.py:140-173 | test_inline_web_edit (pass) | APPROVED |
| Caption update | Cancel inline edit | cancel-edit returns the original card; unknown post id closes the form without changes | apps/web/post_views.py:140-147 | test_cancel_inline_edit, test_cancel_inline_edit_unknown_post_id_closes_without_change (pass) | APPROVED |
| Post deletion | Owner deletes post via API | DELETE /api/posts/<uuid>/ → 204; media cascade-deleted | apps/posts/services.py (delete) | test_owner_deletes_post_via_api (pass) | APPROVED |
| Post deletion | Non-owner deletion rejected | Use case consumes Post.can_delete; 403 with the exact text "You can only delete your own posts" | apps/posts/use_cases.py:191-193 | test_non_owner_deletion_rejected (pass) | APPROVED |
| Post deletion | Web deletion removes the card | HTMX delete endpoint swaps the card away and toasts "Post deleted!" | apps/web/post_views.py:176-189 | test_web_deletion_removes_the_card (pass) | APPROVED |
| Post visibility | No cross-user listing | Every listing path filters by owner; after the adversarial pass the detail/read paths also enforce ownership (404 for non-owners) | apps/posts/services.py:36; apps/posts/use_cases.py (GetPost) | test_no_cross_user_listing (pass); test_atk001 + re-attack bypass probes (pass) | APPROVED |
| user-accounts (MODIFIED) | Placeholder requires login / Logged-in user reaches the placeholder | /web/feed/ stays login-required and now renders the personal posts feed | apps/web/views.py:120 | test_web_post_actions_require_login, test_personal_feed_on_the_feed_page (pass) | APPROVED |

### Quality gates (actual results)
pytest 259/259 passed (2 xfailed) · coverage 99.42% (target >= 80) · ruff: 0 issues ·
mypy: 0 errors · manage.py check + makemigrations --check clean · OpenAPI schema
includes GET/POST /api/posts/ and GET/PATCH/DELETE /api/posts/{id}/

### Adversarial pass (The Bad)
- Attack 1 (2 iterations, ~4 min, 6/6 test runs): 54 attack tests; 2 blocking bugs found:
  - BUG-001 cross-user post visibility (GET detail + web edit-form/cancel-edit leaked
    other users' posts) → fixed: GetPostUseCase now takes the requesting user and maps
    non-owners to "Post not found"; web edit-form/cancel-edit return an empty response →
    regression tests test_atk001*, test_atk_w03a/b in the suite
  - BUG-002 500 on limit/offset/page > 2^63-1 (SQLite binding overflow) → fixed:
    PostService.list_for_user clamps limit/offset at 2^63-1 (single chokepoint for API
    and web) → regression tests test_atk005b, test_atk_w05a in the suite
- Re-attack (1 iteration, 6/6 min, 6/6 runs): both fixes verified against direct bypass
  attempts (list serializer, 404 bodies, feed page, clamp boundary exactly at 2^63-1 and
  beyond, owner-flow regressions). SURVIVES. 21 new tests joined the suite
  (test_bad_attacks_posts_reattack.py, test_bad_attacks_posts_web_reattack.py).
- Non-blocking observations: unauthenticated /api/posts/ answers 403 not 401
  (spec-silent); whitespace-only caption normalized to empty on the API but stored
  verbatim on the web edit path (spec-silent divergence); null byte in caption stored
  verbatim (no crash); media storage dedups colliding filenames with random suffixes
  (accepted in design.md).
- Budget: 10 min used total, 12 test runs across two cycles (limits per cycle: 6 min,
  6 runs, 2 iterations — re-attack cycle granted by the orchestrator after the fix,
  documented in gbu-state.json)

### Deviations and assumptions
- Web post routes live in apps/posts/web_urls.py included under /web/posts/ from
  apps/web/urls.py (task 1.1 allowed this option) — keeps posts routing inside the
  posts domain.
- PostMedia uses a UniqueConstraint(post, order) instead of a plain index (task 1.2
  allowed either) — guarantees consistent ordering and provides the index.
- The personal feed replaces the /web/feed/ placeholder (this repo's landing page)
  rather than a new home page — recorded as an agent-decided business decision in
  proposal.md and handled by a MODIFIED delta on user-accounts.
- BUG-002 was fixed by clamping instead of answering 400 because the Bad's regression
  test (unmodifiable) pins 200-with-empty-window for huge values.
- HTMX toasts on the partial flows (edit/delete) render inline in the swap response;
  the create flow uses the messages framework. Spec pins only the exact toast texts.
- Task 4.1 said "base.html"; the project's base template is base_auth.html — htmx was
  added there (cosmetic naming only).

### Manual validation pointers (optional for the Sheriff)
- Run the dev server (`manage.py runserver`), register/login and use /web/feed/:
  create several posts (toast + placeholder image), edit a caption inline, cancel the
  edit, delete a card, paginate with the prev/next controls.
- Open /docs/ and exercise POST/GET /api/posts/ with JWT from /api/auth/login/.
- Check /schema/ contains the six /api/posts/ operations.

### Sheriff decision
[x] SI — proceed to verify/archive (2026-11-06: verified CLEAN, synced and archived)
