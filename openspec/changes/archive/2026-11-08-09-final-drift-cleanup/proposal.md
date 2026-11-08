# Proposal — 09-final-drift-cleanup

## Why

The cycle-8 audit left six low findings (three carried from cycle 7, three
new). All are one-line declarations, one test alias, or policy text. This
mini change resolves all six so the next audit returns IN SYNC literal and
the specification-driven build is complete.

## What Changes

- user-accounts "API JWT login": declare the session-auth precedence
  (an authenticated session wins over any presented JWT) and the CSRF
  enforcement on session-authenticated unsafe methods (C7-02), and declare
  the anonymous-failure surface — DRF-guarded endpoints answer 403 without
  a WWW-Authenticate challenge (C7-03, Sheriff's declared default).
- Tests: add the thin scenario-named alias test_topbar_links_to_own_profile
  for the social twin scenario (C7-01).
- web-ui "Brand naming": scope the footer clause to the home feed ("and
  only on the home feed") so the absence elsewhere is declared (C8-02), and
  narrow the titles scenario to "any page of the web UI" (C8-03 — Swagger
  and admin declare themselves as separate surfaces).
- workflow: declare the post-exhaustion practice in the GBU budget policy —
  when Bad's budget is exhausted, the remaining surface is verified by the
  orchestrator with the full suite and Ugly static checks, reported
  honestly (C8-01).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `user-accounts`: API JWT login (+2 scenarios).
- `web-ui`: Brand naming (text scoping, scenarios unchanged).

## Impact

- One delta requirement with 2 new scenarios, one delta requirement with
  text-only scoping, one test alias, one workflow paragraph. No production
  code changes; no behavior changes.

## Business Decisions

| Date       | Decision                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | C7-02: session identity wins over a presented JWT; CSRF is enforced on session-authenticated unsafe methods.     |
| 2026-11-08 | C7-03: anonymous API requests are rejected 403 without a WWW-Authenticate challenge (declared, not changed).      |
| 2026-11-08 | C8-01: post-exhaustion verification by the orchestrator (full suite + Ugly) is the declared practice.            |
| 2026-11-08 | C8-03: the brand-titles scenario covers the web UI only; Swagger/admin are separate surfaces.                    |
