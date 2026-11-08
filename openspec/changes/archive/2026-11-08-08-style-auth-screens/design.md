# Design

## Context

The auth layout (`base_auth.html`, `login.html`, `register.html`,
`partials/auth_logo.html`, the auth-* block of `web/style.css`) already
renders the declared structure: centered auth card with logo and form,
secondary card, footer, no sidebar. The Sheriff wants it to look like the
brand without touching behavior.

## Goals / Non-Goals

**Goals:**

- Auth screens visually match the brand target (fonts + gradient).
- Every currently declared element and test assertion stays intact.

**Non-Goals:**

- Restyling the authenticated app (feed, profile, posts) — later change.
- Any form/validation/routing change; any new endpoint or template element
  beyond styling hooks.

## Decisions

1. **Fonts via one Google Fonts link in `base_auth.html`**: "Grand Hotel"
   (logo script) + "Inter" (body). The logo partial gains a class hook
   (`auth-logo-brand`) so the script font applies via CSS — the `bi
   bi-instagram` icon and `data-testid="auth-logo"` stay (tests pin them).
2. **Gradient on the `auth-page` background** in CSS; cards stay light with
   refined spacing/typography. Pure CSS — no HTML structure changes beyond
   the fonts link and the logo class.
3. **Testability**: the new scenario is asserted by presence of the fonts
   link and the gradient class on both auth pages (rendering itself is not
   verifiable in the sandbox — consistent with the audit's standing caveat).

## Risks / Trade-offs

- [Google Fonts requires network at runtime] → The config already declares
  Google Fonts as the target stack; degradation to system fonts is graceful
  (font-family fallbacks in CSS).
- [Restyling could break the pinned auth-card tests] → The existing tests
  assert element presence (logo testid, form fields, links) — none are
  removed; the suite gate catches any drift.

## Open Questions

None.
