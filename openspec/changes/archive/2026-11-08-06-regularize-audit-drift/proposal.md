# Proposal — 06-regularize-audit-drift

## Why

Five implementation cycles left the living specs and the code behaviorally
coherent on every specified flow, but the accumulated audits
(`openspec/audit-cycle-{1..5}-findings.md`) list ~24 open findings: behavior
that is real, tested and desirable but declared by no scenario, tests that
pin unspecified behavior, a handful of genuine code defects (broken card
links, broken `createsuperuser`, plain-text passwords on the bulk path, a
missing declared bootstrap) and spec/code tensions in the UI structure. This
change regularizes all findings with an uncontroversial resolution so the
next audit returns IN SYNC; the two remaining business-UX escalations are
declared here with their chosen defaults.

## What Changes

- user-accounts: declare the `save()` silent-refusal contract (F-04), the
  hashed-password rule on every storage path including bulk writes (F-03),
  the authenticated-login-page redirect (F-09) and the byte-exact,
  whitespace-rejecting username rule on the API path (F-05/F-07 — the API
  stops trimming and rejects padded usernames like the web already does).
  Email uniqueness is declared byte-exact/case-sensitive (F-06) and the
  strict-xfail probe is replaced by a real test.
- Restore `create_user`/`create_superuser` on the user manager so Django's
  stock tooling (`createsuperuser`) works (F-02).
- Land the declared `accounts.0003` bootstrap migration that ensures the dev
  superuser `bob` (F-01), DEBUG-guarded so production migrations never
  create it.
- posts: fix the post-card header links to point at the owner's profile page
  (N-05 — the only guaranteed-broken user-visible link), declare the
  pagination-parameters 400 (N-04), declare the web inline-edit routing
  contract (N-06) and add the missing scenario-named media-path test (N-02).
- stories: declare the non-HTMX redirect fallback for create/view (W-1), the
  malformed-identifier 404 (C4-01) and the ORM bulk-path expiry contract
  (C4-02).
- social: declare the profile page's non-HTMX full-page window (C5-01).
- web-ui: mark Profile active on profile pages so "Active navigation state"
  holds everywhere (S-01) and declare the full-card grid item anatomy
  (S-02); the card anatomy requirement itself needs no text change once
  N-05 is fixed.
- admin-console: declare that Django's auto-registered auth Group management
  is also offered (C5-02).
- config: reword the fixed-stack frontend line so gradients and Google Fonts
  are stated as targets, not claims (F-10).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `user-accounts`: User account data (save contract, bulk hashing, API
  whitespace rule), Web session login (authenticated redirect).
- `posts`: Post listing (pagination 400), Caption update (web routing
  contract).
- `stories`: Story data model (bulk-path expiry contract), Story creation
  and Story view tracking (non-HTMX fallback, malformed identifier).
- `social`: User profile page (non-HTMX full-page window).
- `web-ui`: Profile page structure (full-card grid anatomy).
- `admin-console`: Django admin console (auth Group management).

## Impact

- Spec deltas carry every existing scenario plus the declared ones (each new
  scenario gets a scenario-named test).
- Code fixes: post_card.html links, accounts manager methods, bulk hashing,
  one data migration, serializer whitespace rule, sidebar active state.
- Test updates: the API-trim probe, the email-case xfail, the bulk-create
  pin and the card-link pin switch to the regularized contracts.
- No new endpoints, models or dependencies; `makemigrations` gains one data
  migration.

## Business Decisions

| Date       | Decision                                                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | Usernames with surrounding whitespace are REJECTED on every registration path (API aligns with the web; DRF trimming removed).   |
| 2026-11-08 | Email uniqueness stays byte-exact/case-sensitive, matching the password comparison rule; the xfail probe becomes a real test.    |
| 2026-11-08 | Passwords are hashed on every storage path: `bulk_create` hashes like `save()`/`create()` already do.                            |
| 2026-11-08 | The `accounts.0003` bootstrap migration creates the dev superuser `bob` only when `settings.DEBUG` is on.                        |
| 2026-11-08 | Post-card header links point at `/web/profile/<owner-uuid>/` (the living spec's "linked to their profile page").                 |
| 2026-11-08 | Profile grid items render the full post-card anatomy (design Decision 4 of 03-add-social wins over the narrower delta wording).  |
| 2026-11-08 | Django's auto-registered auth Group management stays in the admin and is declared.                                              |
| 2026-11-08 | Out of scope (remain documented escalations): W-2 budget policy; visual styling (gradients/fonts stay a target in config).       |
