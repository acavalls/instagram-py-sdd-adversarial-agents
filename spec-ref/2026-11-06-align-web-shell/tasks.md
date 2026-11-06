# Tasks

## 1. Icon font and base shell

- [x] 1.1 Add the Bootstrap Icons CDN stylesheet to `base.html` and the new `base_auth.html`
- [x] 1.2 Replace the topbar in `base.html` with the sidebar structure (logo, nav links, Create form, Profile link, logout at bottom, `#messages` and `#modal-container` preserved)

## 2. Sidebar styles

- [x] 2.1 Add sidebar CSS to `web.css` (fixed layout, link states, active state, logo) with responsive collapse at 1024px (icon-only) and 768px (bottom bar), and the `main-content` offset

## 3. Auth layout

- [x] 3.1 Add `base_auth.html` (auth-page body, phone-gradient frame, footer links) and its CSS (auth layout, auth card)
- [x] 3.2 Rework `login.html` and `register.html` to extend `base_auth.html` with auth cards (logo, fields, submit, secondary link card)

## 4. Tests

- [x] 4.1 Add `apps/web/tests/test_web_ui.py` with scenario-traceable tests: sidebar navigation entries, profile link to own profile, active state on home, anonymous login renders auth layout without sidebar, logout at sidebar bottom, icon font loaded, login auth card, register auth card
- [x] 4.2 Update `test_topbar_links_to_own_profile` (social) to assert the sidebar Profile link; keep the anonymous no-leak test

## 5. Quality gates

- [x] 5.1 Run full pytest suite (all pass, previous 160 preserved modulo renamed assertions) and coverage (>= 80%)
- [x] 5.2 Run ruff and mypy clean
- [x] 5.3 Manual smoke: dev server — sidebar renders with active states, icons visible, login/register in auth layout, responsive collapse

## Workflow follow-up

- Commit implementation (super-commit at the gate)
- Verify the change (`/opsx-verify`)
- Archive the change (`/opsx-archive`)
