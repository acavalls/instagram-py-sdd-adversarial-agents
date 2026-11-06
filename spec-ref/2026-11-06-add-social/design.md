# Design: add-social

## Context

The reference app implements the social layer in `apps/social/` (Follow
model, FollowService, FeedService, four use cases) and exposes it only
through the web UI (HTMX follow buttons, profile page, following modal).
Our clone already has a first-class REST API surface (`/api/posts/`,
`/api/auth/`), so this change mirrors the reference domain layer and adds a
social API as a deliberate deviation.

This change also absorbs the six low-severity findings of the 2026-11-05
spec-audit (F1–F6), per the user's decision.

## Goals

- Non-goals: stories (`add-stories`), real file upload UX, followers list
  modal (only the following list, as in the reference), notifications.

## Decisions

1. **Follow model mirrors the reference** (`apps/social/models.py`): UUID pk,
   `follower`/`following` FKs with `related_name="following"`/`"followers"`,
   `unique_together` pair, `CheckConstraint no_self_follow`, indexes on
   `(follower, -created_at)` and `(following, -created_at)`. Service-level
   checks return the reference error strings ("You cannot follow yourself",
   "Already following this user", "Follow relationship not found").

2. **Services mirror the reference**: `FollowService` (follow/unfollow/
   is_following/get_following/get_followers) and `FeedService` (list_feed
   subquery on Follow, get_suggestions excluding self and followed users,
   ordered by `-date_joined`, limit 5).

3. **Home feed semantics change** (the core behavioral change): `web.index`
   switches from `PostService.list_for_user` to `ListFeedUseCase`
   (FeedService). Own posts remain reachable through the owner's profile
   grid and `GET /api/posts/`. The posts spec delta MODIFIES `Post listing`
   and `Post visibility` accordingly. Edit/delete controls on home cards
   become moot (home shows others' posts); they live on the profile grid,
   which makes the existing "profile grid" wording of the posts spec
   accurate (resolves audit finding F2 without a spec edit).

4. **Pagination, not infinite scroll** (deviation D1 from the reference):
   the reference uses HTMX infinite scroll on feed and profile; our clone
   already uses page-param pagination with prev/next links (12 per page,
   `POSTS_PER_PAGE`). We keep it for consistency and simplicity; the spec
   only requires "paginated" so no drift.

5. **Social layer is web-only** (user decision 2026-11-05, reference
   parity): no social REST endpoints are added — the reference app exposes
   social exclusively through the web UI, and the user chose to match it.
   The domain layer (services/use cases) stays reusable so a social API can
   be regularized later with an explicit OpenSpec change if ever needed.

6. **Web follow/unfollow via HTMX** (reference pattern): `follow_user` /
   `unfollow_user` views return the `_follow_button.html` partial with the
   new state plus toast, using the shared `_messages.html` include. Toast
   texts: "Followed successfully" / "Unfollowed successfully" (reference).

7. **Profile page behind login** (deviation D3 from the reference, which
   allows anonymous profile views): our user-accounts spec mandates
   "Protected pages require login"; `profile_view` keeps `@login_required`.

8. **Profile implementation**: reuse `PostService.list_for_user` for the
   grid (12 per page, same pagination partials as home), counters via
   `Post.count()` / `Follow` queries, `is_own_profile` and `is_following`
   flags for template branching. Unknown user → `Http404`.

9. **Following modal**: `following_list` view renders
   `_following_list_modal.html` with `FollowService.get_following` filtered
   by `q` (icontains on username/first_name/last_name), as in the reference.

10. **F1 fix (caption length)**: `UpdatePostUseCase` rejects captions longer
    than 2200 characters with error "Caption must be 2200 characters or
    fewer" before saving; this closes the web path gap (the API path is
    already covered by the serializer). One new test.

11. **F6 seed command**: `seed_demo_data` management command creates a demo
    ecosystem through the existing use cases/services (users, follows,
    posts with generated placeholders) so the feed, suggestions and
    profiles have data for manual validation; idempotent per run scope
    (skips if users exist).

12. **F3/F4 recorded, not coded**: `/schema/` and `/docs/` get the new
    `api-docs` living spec at archive time (no code changes); Django admin
    stays deliberately out of the spec contract — decision recorded here
    and in the proposal.

## Risks / Trade-offs

- Home feed empty state for new users is intentional (reference behaves the
  same); suggestions panel mitigates it.
- The social API triples the surface but reuses the same service layer; no
  new dependencies.
- `list_feed` uses a subquery on Follow (reference pattern); fine for
  SQLite at this scale.
