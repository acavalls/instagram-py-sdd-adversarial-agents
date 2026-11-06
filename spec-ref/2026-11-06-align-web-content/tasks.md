# Tasks

## 1. Feed infinite scroll

- [x] 1.1 Add the HX branch to `index`: `HX-Request` renders `_feed_posts.html` partial (cards + sentinel/end) instead of the full page
- [x] 1.2 Create `_feed_posts.html` (cards loop, sentinel with `hx-trigger="revealed"`, loader spinner, "No more posts" end) and rework `index.html` (feed container `#feed-posts`, empty state with icon/title/CTA)

## 2. Profile infinite scroll

- [x] 2.1 Add the HX branch to `profile_view` rendering `_profile_posts.html` (grid wrappers with overlay, own-profile edit/delete menu, sentinel)
- [x] 2.2 Rework `profile.html`: header (large avatar, stats with following-modal link, tabs bar POSTS/SAVED/TAGGED), grid container `#profile-posts`

## 3. Post card and suggestions

- [x] 3.1 Upgrade `_post_card.html` to the reference anatomy (header avatar + username link, actions row placeholders, media placeholder icon, caption + relative time, owner menu preserved)
- [x] 3.2 Create `_feed_sidebar.html` (current-user block, suggestions with avatar/username/reason/follow button, footer) and wire it into `index.html`

## 4. CSS

- [x] 4.1 Add CSS for sentinel/loader/spinner, post-card header/actions, profile header/tabs/grid overlay, feed sidebar, empty state

## 5. Tests

- [x] 5.1 Update feed pagination tests to scroll semantics (HX partial for page 2, sentinel/end markers) and add "Feed loads more posts on scroll" test
- [x] 5.2 Add profile scroll test ("Profile grid loads more posts on scroll") and update existing profile assertions
- [x] 5.3 Add web-ui content tests: card header/actions/placeholder, profile header/tabs/following-stat link/grid overlay, empty feed state, suggestions panel
- [x] 5.4 Update social tests impacted by new markup (empty state, suggestions) keeping scenario traceability

## 6. Quality gates

- [x] 6.1 Run full pytest suite (all pass) and coverage (>= 80%)
- [x] 6.2 Run ruff and mypy clean
- [x] 6.3 Manual smoke: dev server — feed loads 12 posts then more on scroll, profile grid scrolls, card anatomy, suggestions with follow buttons, empty state

## Workflow follow-up

- Commit implementation (super-commit at the gate)
- Verify the change (`/opsx-verify`)
- Archive the change (`/opsx-archive`)
