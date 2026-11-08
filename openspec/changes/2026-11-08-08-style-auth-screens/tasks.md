# Tasks

## 1. Auth visual restyle (web-ui delta)

- [ ] 1.1 Add the Google Fonts link (Grand Hotel + Inter) to `base_auth.html` and the brand class hook to the logo partial; restyle the auth surface in `web/style.css` only (gradient background on `auth-page`, brand typography for logo/forms, card polish); no HTML structure changes beyond the link and the logo class
- [ ] 1.2 Declare the new scenario in the delta spec and add its scenario-named test (fonts link + gradient class present on login and register; existing auth tests untouched and green)

  - Manual validation: open `/web/login/` and `/web/register/` — gradient
    background, script-font logo, polished card; login still works.

## 2. Config wording and gates

- [ ] 2.1 Update `openspec/config.yaml`: the auth screens now implement the target styling (fonts + gradient shipped on auth pages); the rest of the UI keeps system fonts and the single story-ring gradient
- [ ] 2.2 Run the full gates: `pytest` (coverage >= 80%), `ruff check`, `ruff format --check`, `mypy`, `manage.py check`

## Workflow follow-up

- Archive after review; the delta merges into `openspec/specs/web-ui/spec.md`.
