# Changelog

## 2026-11-06 — regularize-audit-drifts-3

Regularization of the 8 low findings from audit #6 (post align-web-content).
No code behavior changes.

- MODIFIED `social` / Followed-users feed: secondary empty state "No posts
  yet" for follows-without-posts (F1).
- MODIFIED `social` / User suggestions: sidebar panel chrome (current-user
  block, footer links) and "No suggestions available." empty message (F3).
- MODIFIED `social` / User profile page: empty grid message (F2).
- MODIFIED `posts` / Post listing: non-HTMX GET with `?page=` renders the
  full page at that window (F4; spec adopts actual code behavior).
- MODIFIED `web-ui` / Post card anatomy + Profile page structure: posts with
  multiple media render only the first media file (F6).
- Tests: empty-feed icon assertion (F5) and scenario docstrings on 4
  supplementary tests (F8).
- config.yaml: `seed_data` → `seed_demo_data` (F7).

Commits: plan 6d81484; impl 66564a2 (docs), d128d50 (test), c54f29f (chore);
archive <this commit>.
