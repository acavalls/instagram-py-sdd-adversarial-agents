# Proposal — 08-style-auth-screens

## Why

The Sheriff asked for a visual improvement of the login screen (and its
twin, the register page — they share the auth layout). The config's fixed
stack declares a visual target (Google Fonts + gradients) that the shipped
UI does not implement yet; the auth screens are the chosen first surface.
This is a pure restyle: no form, validation, routing or behavior changes.

## What Changes

- The auth layout loads the brand Google Fonts (a script display font for
  the logo, a body font for the forms) and paints the auth background with
  the brand gradient; the auth card gets polished typography and spacing.
- All currently declared auth-layout elements stay exactly as they are:
  logo, form, secondary card, footer links, no sidebar.
- web-ui "Auth layout": declare the brand visual style (fonts + gradient)
  and add one scenario asserting it.
- config: update the fixed-stack frontend line — the auth screens now
  implement the target styling (the rest of the UI keeps system fonts and
  its single story-ring gradient).
- Rebrand the visible product name from "django_ig" to "Instagram":
  page titles, the sidebar brand and footer copy, the auth logo wordmark
  and the OpenAPI title/description (Sheriff's PAUSE-1 feedback).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `web-ui`: Auth layout (+1 scenario, restyled requirement text) and a new
  Brand naming requirement (+3 scenarios).

## Impact

- `base_auth.html` (fonts link), `web/style.css` (auth styles only),
  one new scenario-named test. Zero production-code behavior changes; the
  existing auth tests must keep passing untouched.

## Business Decisions

| Date       | Decision                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | Scope is visual only: no UX/validation changes (Sheriff's choice).                                                                      |
| 2026-11-08 | Brand fonts: "Grand Hotel" for the logo (Instagram-clone convention) and "Inter" for body text, loaded from Google Fonts in the auth layout. |
| 2026-11-08 | The brand gradient (Instagram-like purple/pink/orange) paints the auth page background; the cards stay light.                            |
| 2026-11-08 | The rest of the app is NOT restyled in this change (system fonts stay) — the config target line is updated to say so.                    |
| 2026-11-08 | The visible product name is "Instagram" everywhere (titles, sidebar, auth wordmark, OpenAPI title) — Sheriff's decision at PAUSE-1.        |
