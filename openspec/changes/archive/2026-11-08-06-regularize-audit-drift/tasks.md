# Tasks

Ordering premise: inside-out WITHIN each task; each group is
validation-closed, with its Manual validation line.

## 1. Accounts regularization (user-accounts delta; F-01, F-02, F-03, F-04, F-05/F-07, F-06, F-09)

- [x] 1.1 Restore `create_user`/`create_superuser` on `UserManager` (F-02); make `UserQuerySet.bulk_create` hash passwords like the save path (F-03); update the bulk-create pin test accordingly; test: `createsuperuser` works via `call_command`, bulk-created passwords authenticate and are never stored raw
- [x] 1.2 Add the `accounts.0003` data migration creating the dev superuser `bob` only under `settings.DEBUG` and only if absent (F-01); tests: the migration function creates bob under DEBUG and creates nobody with DEBUG off
- [x] 1.3 Remove DRF username trimming so padded usernames are rejected on the API path (F-05/F-07); make email storage byte-exact by overriding `User.clean` to skip the email domain normalization and by mapping username/email duplicates distinctly in the register use case (F-06); tests: API rejects `"  padded  "` with the username error, `FOO@x.com` and `foo@X.COM` are accepted byte-exactly while `foo@x.com` exists (stored value keeps the registrant's case on both the use-case and web paths), same-case duplicate is rejected with `Email already registered`
- [x] 1.4 Declare the new user-accounts scenarios (save() silent refusal, bulk hashing, authenticated login redirect) and add their scenario-named tests (F-04, F-03, F-09)

  - Manual validation: `manage.py createsuperuser` completes; migrate on a
    fresh dev DB creates `bob`; register a padded username from the API and
    the web — both reject.

## 2. Posts regularization (posts delta; N-02, N-04, N-05, N-06)

- [x] 2.1 Point the post-card header's avatar and username links at `web:profile` (owner UUID) and update every test pinning `/web/users/<username>/` (N-05)
- [x] 2.2 Declare the new posts scenarios (pagination 400, web edit GET refusal, non-owner web edit POST) and add their scenario-named tests (N-04, N-06); add the missing `test_media_stored_under_the_post_media_path` (N-02)

  - Manual validation: every post card's username link opens the owner's
    profile page; `GET /api/posts/?limit=0` returns 400; a non-owner GET of
    an edit form returns 404 without leaking the caption.

## 3. Stories regularization (stories delta; W-1, C4-01, C4-02)

- [x] 3.1 Declare the new stories scenarios (non-HTMX create/view fallback redirect, malformed identifier 404, bulk-path expiry contract) and add their scenario-named tests (W-1, C4-01, C4-02)

  - Manual validation: a plain (non-HTMX) POST to `/web/stories/create/`
    redirects to the feed; `POST /web/stories/not-a-uuid/view/` returns 404.

## 4. Web, social and admin regularization (social, web-ui, admin-console deltas; C5-01, C5-02, S-01, S-02)

- [x] 4.1 Mark Profile active on profile pages (and the following modal) so "Active navigation state" holds everywhere (S-01); tests: profile pages render the Profile entry with the active class and NOT Home
- [x] 4.2 Declare the new social/web-ui/admin-console scenarios (non-HTMX profile window, full-card grid anatomy, auth Group management) and add their scenario-named tests (C5-01, S-02, C5-02)

  - Manual validation: a profile page highlights Profile in the sidebar;
    `/web/profile/<uuid>/?page=2` without HTMX renders the full page with
    that window; the admin index offers Groups.

## 5. Config wording and quality gates

- [x] 5.1 Reword the fixed-stack frontend line in `openspec/config.yaml` so gradients and Google Fonts are stated as targets (F-10)
- [x] 5.2 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green

## Workflow follow-up

- Archive the change after review; the deltas merge into
  `openspec/specs/{user-accounts,posts,stories,social,web-ui,admin-console}/
  spec.md`.
