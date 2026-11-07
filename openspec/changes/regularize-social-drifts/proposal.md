# Proposal

## Why

The 2026-11-07 post-add-social spec audit found LIGHT DRIFT: the new
social/api-docs surface is in sync, but carried-over findings from the
2026-11-06 add-posts audit (CS-001, CS-002, CS-003, CS-004, TS-001, TS-002),
plus new low findings from the social cycle (concurrent follow race, modal
search wildcards, stale "feed grid" wording, stale config claim), leave code
and living specs divergent. This change regularizes them so the next audit
returns IN SYNC.

## What Changes

**Code fixes (spec is already right, code follows it):**

- Deterministic post ordering: tiebreaker `-id` added after `-created_at` in
  the Post model ordering and the feed query, so pagination windows cannot
  duplicate or skip rows on timestamp ties (audit F-02 / CS-002).
- Media-count invariant on every persistence path: a model-level guard
  mirroring the caption save-guard rejects attaching an 11th media file
  (audit F-03 / CS-001).
- Username rule on every storage path: queryset `update()`/`bulk_create()`
  for users go through the same username validation as `save()`; the
  documenting xfail becomes a passing test (audit F-04 / CS-004).
- Concurrent duplicate follow keeps the reference contract: the follow
  service translates the DB IntegrityError race into
  "Already following this user" instead of a 500 (audit F-05, GBU OBS-S004).
- Following-modal search matches the query literally: SQL LIKE wildcards
  (`%`, `_`) in the search text are escaped, so `q=100%` finds usernames
  containing "100%" (audit F-06, GBU OBS-S001). Agent decision: literal
  substring match is the reasonable semantics; the spec already says
  "matches the query".
- `create_user(None)` raises the model's username validation error instead
  of an opaque TypeError; the deferral xfail becomes a passing test
  (audit F-10 / TS-002).

**Spec deltas (code is already right, spec follows it):**

- `posts` MODIFIED `Post data model`/`Post listing`/`Post creation`/
  `Caption update`/`Post deletion`:
  - post cards show the post's first media file (single-image cards;
    carousel deliberately out of scope — agent decision 2026-11-07, flagged
    for review; resolves audit F-01 / CS-003);
  - the API trims surrounding whitespace from captions (pinned by existing
    tests, now owned by the spec; audit F-09 / TS-001);
  - "feed grid" wording becomes "profile grid" after the social cycle moved
    the edit/delete controls there (audit F-07).
- `user-accounts` MODIFIED `User account data`/`Web session logout`:
  - passwords are compared and stored byte-exactly (no trimming/folding;
    audit F-09 / TS-001);
  - the username rule holds on every storage path including bulk writes
    (backs the F-04 code fix);
  - web logout is POST-only: non-POST requests respond 405 without clearing
    the session (audit F-09 / TS-001).

**Accepted without changes (decisions recorded in design.md):**

- Django admin surfaces stay out of the spec contract on purpose;
  `FollowAdmin` is dev tooling (audit F-11).
- `seed_demo_data` stays dev tooling owned by `config.yaml` context, which
  now truthfully describes it (audit F-12; closes ENV-001 residue).

**Environment fix:**

- `config.yaml` context reworded from "Django 5+" to "Django 6+" to match
  the actual runtime (audit F-08). Direct edit, no spec delta (not app
  behavior).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `posts`: card media clarification, caption whitespace normalization owned,
  profile-grid wording for web edit/delete.
- `user-accounts`: byte-exact password handling, username rule on bulk
  writes, POST-only logout.

## Impact

- `apps/posts/`: model ordering + media-count guard in `PostMedia.save()`.
- `apps/social/`: follow race translation, search wildcard escaping.
- `apps/accounts/`: user queryset bulk-write validation, manager None guard.
- `openspec/config.yaml`: Django version wording.
- Tests: two xfails become passing tests; new regression tests for the
  ordering tiebreaker, media guard, race translation, wildcard escaping and
  bulk-write validation.
