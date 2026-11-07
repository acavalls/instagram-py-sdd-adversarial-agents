# Design: add-social

## Context

This clone already has first-class REST API surfaces (`/api/posts/`,
`/api/auth/`) and a personal home feed (`apps/web/views.py:feed` using
`ListPostsUseCase`). The reference app implements the social layer in
`apps/social/` (Follow model, FollowService, FeedService, four use cases)
and exposes it only through the web UI (HTMX follow buttons, profile page,
following modal). This change mirrors the reference domain layer, adapted to
this repo's single-module layout (`services.py` / `use_cases.py` per app).

Grounding differences from the reference snapshot (spec-ref
`2026-11-06-add-social`) found by inspecting this codebase:

- F1 (caption length in the web update path) is ALREADY enforced here:
  `apps/web/post_views.py` checks the length before calling
  `UpdatePostUseCase`, and `Post.save()` enforces the limit on every
  persistence path. The snapshot's code task collapses to adding the missing
  regression test only.
- F3 (`/schema/` and `/docs/`) already exists in `config/urls.py`
  (drf-spectacular). The api-docs capability only lands the living spec; the
  snapshot's smoke-check becomes the scenario tests.
- F5 (media storage) documents THIS repo's convention: `upload_to="post_media/"`
  flat path (`apps/posts/models.py`), not the reference's dated
  `post_examples/<y>/<m>/<d>/` path. The delta spec describes the real code.
- F6 (`seed_demo_data`) does not exist here; it is built now and also closes
  audit finding ENV-001 of the 2026-11-06 add-posts audit.

The 2026-11-06 audit findings CS-001 (media cap at service level), CS-002
(post ordering tiebreaker), CS-003 (carousel card), CS-004 (bulk bypass) and
TS-002 (xfail BUG-005) stay pending for a future regularization cycle; they
are independent of the social layer.

## Goals

- Non-goals: stories (`add-stories`), followers list modal (only the
  following list, as in the reference), notifications, real file upload UX,
  social REST endpoints.

## Decisions

1. **Follow model mirrors the reference** (`apps/social/models.py`): UUID pk,
   `follower`/`following` FKs with `related_name="following"`/`"followers"`,
   `unique_together` pair, `CheckConstraint no_self_follow`, indexes on
   `(follower, -created_at)` and `(following, -created_at)`. Service-level
   checks return the reference error strings ("You cannot follow yourself",
   "Already following this user", "Follow relationship not found").
   Decision: agent-decided (2026-11-07), following the reference snapshot.

2. **Services mirror the reference**: `FollowService` (follow/unfollow/
   is_following/get_following/get_followers) and `FeedService` (list_feed
   subquery on Follow, get_suggestions excluding self and followed users,
   ordered by `-date_joined`, limit 5). Decision: agent-decided (2026-11-07).

3. **Home feed semantics change** (core behavioral change): `web.feed`
   switches from `ListPostsUseCase` to `ListFeedUseCase` (FeedService). Own
   posts remain reachable through the owner's profile grid and
   `GET /api/posts/`. The posts delta MODIFIES `Post listing` and
   `Post visibility` accordingly. Edit/delete controls on home cards become
   moot (home shows others' posts); they live on the profile grid, which
   makes the posts spec's existing "profile grid" wording accurate.
   Decision: agent-decided (2026-11-07), per the snapshot design.

4. **Pagination, not infinite scroll**: keep the existing page-param
   prev/next window (`FEED_PAGE_SIZE`, 12 per page) for consistency and
   simplicity; the spec only requires "paginated". Decision: agent-decided
   (2026-11-07).

5. **Social layer is web-only** (user decision 2026-11-05, recorded in the
   snapshot): no social REST endpoints are added; the reference app exposes
   social exclusively through the web UI. The domain layer stays reusable so
   a social API can be regularized later with an explicit OpenSpec change.

6. **Web follow/unfollow via HTMX** (reference pattern): `follow_user` /
   `unfollow_user` views return the `_follow_button.html` partial with the
   new state plus toast, using the shared messages include. Toast texts:
   "Followed successfully" / "Unfollowed successfully". Decision:
   agent-decided (2026-11-07).

7. **Profile page behind login** (deviation from the reference, which allows
   anonymous profile views): the user-accounts spec mandates "Protected pages
   require login"; `profile_view` keeps `@login_required`. Decision:
   agent-decided (2026-11-07), spec-driven.

8. **Profile implementation**: reuse `PostService.list_for_user` for the
   grid (12 per page, same pagination partials as home), counters via
   `Post.count()` / `Follow` queries, `is_own_profile` and `is_following`
   flags for template branching. Unknown user → `Http404`. Decision:
   agent-decided (2026-11-07).

9. **Following modal**: `following_list` view renders
   `_following_list_modal.html` with `FollowService.get_following` filtered
   by `q` (icontains on username/first_name/last_name), as in the reference.
   Decision: agent-decided (2026-11-07).

10. **Web caption-limit regression test only** (adapted regularization): no
    code change needed (guard already exists at the web view and in
    `Post.save()`); add one test pinning that an oversized caption via
    `submit_edit` does not change the post. Decision: agent-decided
    (2026-11-07), grounded in this codebase's state.

11. **Seed command**: `seed_demo_data` management command creates a demo
    ecosystem through the existing use cases/services (users, follows among
    them, posts with generated placeholders) so the feed, suggestions and
    profiles have data for manual validation; idempotent per run scope
    (skips if demo users exist). Decision: agent-decided (2026-11-07).

12. **api-docs is spec-only**: `/schema/` and `/docs/` already work; the
    capability lands as a living spec with its two scenario tests. Decision:
    agent-decided (2026-11-07).

13. **user-accounts delta added during global verify** (2026-11-07): the
    global Ugly verify found that the living requirement
    "Authenticated landing placeholder" still normatively described the
    own-posts feed page, which would contradict the posts/social deltas
    after archive. The change gains a MODIFIED delta for that requirement:
    the landing feed page shows the followed-users feed owned by the
    `social` capability; own posts stay reachable via the profile grid and
    the posts API. No code change (the implemented behavior already
    matches); the scenario "Logged-in user reaches the placeholder" is
    pinned by the existing followed-feed test
    (`apps/web/tests/test_feed_view.py::test_feed_shows_followed_users_posts_as_cards`,
    plus the login-redirect test for "Placeholder requires login").

## Validation boundaries

- HTTP request format at the edge (views/serializers): page number parsing,
  login requirements, 404 for unknown profiles, POST-only follow endpoints.
- Application rules in use cases: follow/unfollow orchestration, feed and
  suggestion retrieval, error mapping to the reference strings.
- Business invariants in models: unique (follower, following) pair,
  no-self-follow CheckConstraint, caption limit on save.
- Technical constraints in the database: unique_together, check constraint,
  indexes on (follower, -created_at) and (following, -created_at).

Django idiom replaces the ports + fake-adapter pattern of hexagonal
incremental flows: field validators, model save()/full_clean() and managers
act as the value objects and factories; never introduce a repository-ports
layer.

## Risks / Trade-offs

- Home feed empty state for new users is intentional (reference behaves the
  same); suggestions panel mitigates it.
- `list_feed` uses a subquery on Follow (reference pattern); fine for SQLite
  at this scale.
- Follow uniqueness is enforced at DB level; the service checks first to
  return the reference error strings, so IntegrityError never escapes to the
  UI under normal flows.
- No new dependencies.
