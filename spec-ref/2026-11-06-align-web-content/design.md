# Design

## Context

Cycle 2 of the UI/UX parity plan. The shell is aligned (sidebar, icons, auth
layout, `web-ui` capability). Content surfaces still use prev/next links and
the simplified card/profile markup. The reference implements everything this
change ports: HX branches in `index`/`profile_view` returning `_feed_posts.html`/
`_profile_posts.html` partials with a `revealed` sentinel, post card anatomy,
profile header/tabs/overlay grid, empty state, suggestions panel with follow
buttons.

## Goals / Non-Goals

- Goals: infinite scroll on feed and profile grid; post card anatomy; profile
  header/tabs/overlay; empty state; suggestions panel — content parity with
  the reference.
- Non-Goals: functional like/comment/share/save (placeholders, as in the
  reference); functional SAVED/TAGGED tabs; following-list full page (the
  reference view renders the modal only — parity already holds); changing
  page size (keep 12, the reference uses 10/12 — agent decision flagged);
  backend logic changes.

## Decisions

1. **HX branch pattern copied from the reference**: `HX-Request: true` header
   → partial response (`_feed_posts.html` / `_profile_posts.html`) with cards
   + sentinel; plain GET → full page. `next_page` computed in the view.
2. **Sentinel markup**: `hx-get` to the same page URL with `?page=N`,
   `hx-trigger="revealed"`, `hx-swap="beforeend"`, `hx-target` = container id
   (`#feed-posts` / `#profile-posts`), `htmx-indicator` spinner; end marker
   "No more posts" when exhausted. Identical to the reference so future
   diffs stay clean.
3. **Post card actions are placeholders** (`<button>` with `bi-heart` /
   `bi-chat` / `bi-send` / `bi-bookmark`), exactly like the reference — no
   Like/Comment models exist. Owner edit/delete menu preserved on own posts.
4. **Profile grid item**: media (or placeholder icon) inside a link with a
   hover overlay showing like/comment counts as 0 (no counters exist yet —
   same as reference). Own-profile items keep the edit/delete menu inside the
   grid wrapper.
5. **Suggestions panel** replaces the flat list: current-user block,
   "Suggested for you" header, rows with avatar + username + reason + the
   existing `_follow_button.html`, footer links. Follow buttons reuse the
   existing HTMX follow flow (`FollowService`), so no new backend.
6. **Empty feed**: icon + "Share Photos" + subtitle + CTA (dead link, as the
   reference).
7. **Tests**: scenario docstrings traceable ("Feed loads more posts on
   scroll", "Profile grid loads more posts on scroll", "Card header shows...,
   etc."). Existing tests asserting "Older"/"Newer" links are updated to the
   scroll semantics (page-2 HX request returns partial). Pagination-window
   logic itself is unchanged, so those assertions shift to the HX partial.
8. **Page size stays 12** for both feed and grid (agent-decided; reference
   uses 10 feed / 12 profile). Flagged for review.

## Risks / Trade-offs

- Scroll tests rely on `HTTP_HX_REQUEST` header in the test client — stable
  Django test client feature.
- Hover overlay counts are hardcoded 0 like the reference; when a Like model
  ever exists, the overlay and action buttons become functional (future
  extension beyond reference parity).
