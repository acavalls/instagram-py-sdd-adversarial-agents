# Proposal

## Why

Cycle 2 of the UI/UX parity plan with the reference app. The shell is now
aligned (`align-web-shell`); the visible content surfaces still differ: the
reference loads feed and profile pages by HTMX infinite scroll, the post card
has a header (avatar + username) and an actions row, the profile page has a
structured header with avatar/stats/tabs and a hover-overlay grid, the empty
feed shows an icon/title/CTA, and the suggestions panel shows avatars with
follow buttons. This change aligns those behaviors and documents them in the
living specs.

## What Changes

- Home feed and profile grid load additional pages via HTMX infinite scroll
  (`revealed` sentinel, spinner loader, "No more posts" end marker) instead
  of prev/next page links; a plain GET (non-HTMX) still renders the full
  page with the first window.
- Post card gains the reference anatomy: header with owner avatar and
  username link, media placeholder icon, actions row (like, comment, share,
  save — non-functional placeholders, same as the reference), caption with
  owner and relative time; owner edit/delete menu preserved.
- Profile page gains the reference structure: large avatar, stats row
  (posts/followers/following with following opening the modal), tabs bar
  (POSTS active; SAVED/TAGGED placeholders), grid items with hover overlay.
- Empty feed state shows an icon, title "Share Photos", subtitle and CTA.
- Feed sidebar suggestions upgraded: current-user block, suggestion rows
  with avatar, username, reason and a follow button, footer links.
- Deltas: MODIFIED `posts` "Post listing" (feed scroll), MODIFIED `social`
  ("User profile page" grid scroll, "Followed-users feed" empty state,
  "User suggestions" panel), ADDED `web-ui` ("Post card anatomy", "Profile
  page structure").

## Capabilities

### New Capabilities

- (none — extends `web-ui`)

### Modified Capabilities

- `posts`: home feed pagination becomes HTMX infinite scroll.
- `social`: profile grid scroll, empty feed state content, suggestions panel
  presentation.

(ADDED requirements for `web-ui` are part of the new capability's delta.)

## Impact

- **Code**: `apps/web/views.py` (HX branches in `index` and `profile_view`),
  templates (`_feed_posts.html`, `_profile_posts.html`, reworked `index.html`,
  `profile.html`, `_post_card.html`, new `_feed_sidebar.html`), CSS additions,
  tests updated to scroll semantics plus new scenario tests.
- No model, migration, service or use-case changes. No new endpoints.
