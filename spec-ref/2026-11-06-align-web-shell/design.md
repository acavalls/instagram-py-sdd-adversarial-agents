# Design

## Context

The web shell is the largest visible UI/UX divergence from the reference app
(`/home/ale/mapfre/personal/django_ig`): topbar instead of sidebar, icon font
never loaded, generic auth pages. Cycle 1 of the UI/UX parity plan; content
behaviors follow in `align-web-content`. No backend logic is touched.

## Goals / Non-Goals

- Goals: sidebar navigation with active states and placeholder links, icon
  font loading, dedicated auth layout, responsive sidebar collapse — at
  parity with the reference shell.
- Non-Goals: infinite scroll, post card anatomy, profile header/tabs, empty
  states, following-list page (cycle 2); new endpoints; functional Search /
  Explore / Messages / Notifications (placeholders, as in the reference);
  htmx upgrade (stays 1.9.12); replacing the existing color palette.

## Decisions

1. **Port the reference structure, keep our CSS variables.** The templates
   adopt the reference markup (`.sidebar`, `.sidebar__nav`,
   `.sidebar__link--active`, `auth-page`/`auth-layout`/`auth-card` classes)
   so future cycles diff cleanly against `/home/ale/mapfre/personal/django_ig`,
   but colors and fonts keep our existing `web.css` custom properties.

2. **Active state via `request.resolver_match.url_name`**, exactly like the
   reference; no new context processors or template tags.

3. **Bootstrap Icons from CDN** (`cdn.jsdelivr.net` 1.11.3) added to
   `base.html` and `base_auth.html`. Same source as the reference; no vendored
   font (no build step, per config.yaml).

4. **Auth layout ported whole**: `base_auth.html` with the phone-gradient
   frame and footer links, `login.html`/`register.html` as `auth-card`
   blocks. Testability is content-based (body class, card classes, links),
   not pixel-based.

5. **`base.html` keeps the `#messages` container and `#modal-container`**
   (both are load-bearing for existing HTMX flows); messages render inside
   the main content column as before.

6. **Existing topbar tests updated, not deleted**: `test_topbar_links_to_own_profile`
   keeps its scenario docstring ("Topbar links to own profile" stays the
   scenario name — renamed to "Navigation links to own profile" in the delta
   — and the test asserts the sidebar link), the anonymous test keeps
   asserting that no profile link leaks to anonymous pages. The test file
   moves its assertions from `.topbar` markup to `.sidebar` markup.

7. **Create button = existing `create_random_post` form**, same as the
   reference sidebar. No new endpoint.

## Risks / Trade-offs

- Placeholder dead links (`#`) mirror the reference; users may click them and
  get nothing. Accepted for parity; future cycles may implement them.
- CDN dependency for icons: same trade-off as the reference and the Google
  Fonts links already in use.
- The responsive collapse is CSS-only (content assertions cannot test
  breakpoints); verified visually in manual validation.
