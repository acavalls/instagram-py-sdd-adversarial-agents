# Tasks: regularize-social-drifts

## 1. posts domain: deterministic ordering and media-count guard (posts — Post data model, Post listing; audit F-02, F-03)
- [ ] 1.1 `Post.Meta.ordering` becomes `["-created_at", "-id"]`; `FeedService.list_feed` orders by the same pair; test: two posts with identical `created_at` keep a stable, duplicate-free pagination window (scenario: Pagination window)
- [ ] 1.2 `PostMedia.save()` rejects attaching an 11th media file to a post with a field-level ValidationError; tests: model-level rejection on every path, API still answers 400 (scenarios: Post persisted with media, API creation with too many media files)

## 2. accounts domain: username rule on every storage path (user-accounts — User account data; audit F-04, F-10)
- [ ] 2.1 Custom user queryset overrides `update()`/`bulk_create()` to validate the username rule; the bypass-pinning xfail becomes a passing test (scenario: Bulk writes enforce the username rule)
- [ ] 2.2 `create_user(None)` raises the model's username validation error; the deferral xfail becomes a passing test (internal-manager behavior; no spec scenario)

## 3. social domain: follow race and literal search (social — Duplicate follow rejected, Following list search filters; audit F-05, F-06)
- [ ] 3.1 `FollowService.follow` translates the DB IntegrityError race into "Already following this user"; test: monkeypatched race keeps the reference error, exactly one row (scenario: Duplicate follow rejected)
- [ ] 3.2 Following-modal search escapes `%`/`_`/`\` before `icontains`; tests: `q=100%` matches only literal "100%", wildcards no longer match everything (scenario: Following list search filters)

## 4. Spec deltas and environment wording (posts — Post data model/Post listing/Post creation/Caption update/Post deletion; user-accounts — User account data/Web session logout)
- [ ] 4.1 Deltas already landed in `specs/` (posts: first-media card, whitespace caption scenario, profile-grid wording; user-accounts: byte-exact password, bulk-write rule, POST-only logout); verify each new/changed scenario has a traceable passing test and add the missing ones (scenario: Whitespace-only caption becomes empty, Password comparison is byte-exact, Logout is POST-only)
- [ ] 4.2 `config.yaml` context says "Django 6+" (audit F-08; not app behavior, no delta)
