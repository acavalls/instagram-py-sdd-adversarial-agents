# Changelog

## 2026-11-06 — align-web-content

Second UI/UX parity change (cycle 2). Content layer:

- ADDED capability `web-ui`: Post card anatomy (header avatar + username
  link, media placeholder icon, actions row placeholders); Profile page
  structure (large avatar, stats, POSTS/SAVED/TAGGED tabs, grid hover
  overlay).
- MODIFIED `posts` / Post listing: home page loads further feed pages via
  HTMX infinite scroll (sentinel + partial without page shell).
- MODIFIED `social` / Followed-users feed: HTMX infinite scroll pagination;
  empty feed state with "Share Photos" icon/CTA.
- MODIFIED `social` / User suggestions: sidebar suggestion rows with avatar,
  username and follow button.
- MODIFIED `social` / User profile page: grid loads more posts via HTMX
  infinite scroll.

Implementation: `apps/web/views.py` HX branches, `_feed_posts.html`,
`_profile_posts.html`, `_feed_sidebar.html`, `_post_card.html`, reworked
`index.html`/`profile.html`, new `test_web_content.py` (9 tests). Suite 180
passed, coverage 95.49%. Agent decisions flagged: page size 12; action
buttons, SAVED/TAGGED tabs and overlay counts are placeholders (reference
parity).

Commits: plan 9a34efa; impl fa07562 (feat), f15a6ff (test), 533b877
(style), 1e4618e (chore); archive <this commit>.
