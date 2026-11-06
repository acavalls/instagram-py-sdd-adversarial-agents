# Proposal

## Why

UI/UX parity with the reference app is an explicit project goal, and the web
shell is the biggest visible divergence: the reference uses a fixed sidebar
navigation (with active states and a logout entry), loads Bootstrap Icons so
every `bi-*` icon renders, and renders login/register in a dedicated centered
auth layout, while this project uses a minimal topbar, never loads the icon
font (icons are invisible), and renders auth pages in the generic layout.
Cycle 1 of the agreed UI/UX parity plan aligns the global shell; content
behaviors (infinite scroll, post card anatomy, profile header) follow in
`align-web-content`.

## What Changes

- Replace the topbar with a fixed left sidebar for authenticated pages: logo
  link to the home feed, nav links Home / Search / Explore / Messages /
  Notifications / Create / Profile (Search, Explore, Messages, Notifications
  and More are dead placeholder links, mirroring the reference), active link
  highlighted by the current URL name, and the logout form at the sidebar
  bottom.
- Load the Bootstrap Icons stylesheet from CDN in every base template so
  `bi-*` icon classes render visually.
- Render login and register pages in a dedicated auth layout: `auth-page`
  body, centered auth card with logo, secondary card linking to the
  counterpart page, and footer links (port of the reference `base_auth.html`
  structure).
- Update the existing topbar-to-profile requirement (social capability) to
  the sidebar: the navigation shell links to the logged-in user's profile.
- Responsive: the sidebar collapses (icon-only at <=1024px, bottom bar at
  <=768px) per the reference breakpoints.
- Existing tests that assert topbar markup are updated to the sidebar
  semantics; no endpoint, model or business logic changes.

## Capabilities

### New Capabilities

- `web-ui`: the global web shell — sidebar navigation with active states,
  icon font loading, and the dedicated auth layout for login/register.

### Modified Capabilities

- `social`: the "User profile page" requirement no longer mentions a topbar;
  the sidebar (defined in web-ui) links to the logged-in user's own profile.

## Impact

- **Code**: `apps/web/templates/web/base.html` (sidebar replaces topbar),
  new `base_auth.html` usage for login/register, `apps/web/static/web/css/web.css`
  (sidebar, auth-layout, responsive breakpoints), `apps/web/templates/web/login.html`
  /`register.html` (auth cards), tests updated to the new markup.
- **Specs**: new living spec `openspec/specs/web-ui/spec.md`; MODIFIED delta
  for `openspec/specs/social/spec.md`.
- No migrations, no new Python dependencies, no backend behavior changes.
