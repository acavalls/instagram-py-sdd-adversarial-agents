# Design: regularize-social-drifts

## Context

The 2026-11-07 post-add-social audit (LIGHT DRIFT) plus the carried-over
2026-11-06 add-posts findings (CS-001/002/004, TS-001/TS-002) and the GBU
observations from the add-social Bad pass (OBS-S001/S004) leave a set of
low/medium divergences between code and living specs. This change closes
them with the smallest possible edits.

## Goals

- Non-goals: carousels/multi-media card rendering (F-01 resolved as a
  single-image card decision), followers list modal, stories, new features.

## Decisions

1. **Single-image post cards** (resolves audit F-01 / CS-003, business
   decision auto-resolved 2026-11-07, flagged for review): the card shows
   the post's first media file. Simplest behavior consistent with the
   current code and the "simplicity above all" principle; a carousel would
   be a new feature needing its own change. Landing as a posts delta.

2. **Ordering tiebreaker** (F-02 / CS-002): `Post.Meta.ordering` becomes
   `["-created_at", "-id"]` and the feed query orders by the same pair.
   Deterministic pagination windows; no behavior change visible to users
   beyond stability.

3. **Media-count guard** (F-03 / CS-001): `PostMedia.save()` counts the
   post's existing media and raises a ValidationError when attaching an
   11th file, mirroring the caption save-guard pattern (model-level
   invariant, every persistence path). The API serializer keeps its
   earlier, friendlier 400.

4. **Username rule on bulk writes** (F-04 / CS-004): a custom `User`
   queryset overrides `update()` and `bulk_create()` to run the same
   username-format validation as `save()`. The xfail documenting the bypass
   becomes a passing test. (agent-decided 2026-11-07)

5. **Follow race translation** (F-05, OBS-S004): `FollowService.follow`
   catches `IntegrityError` from the DB constraints and re-raises the
   service `ValidationError` with "Already following this user", so the
   losing racer gets the reference toast, never a 500.

6. **Literal search match** (F-06, OBS-S001): the following-modal search
   escapes `%`, `_` and `\` before the `icontains` lookup, making "matches
   the query" literal. (agent-decided 2026-11-07: literal match is the
   reasonable alternative; wildcards in a people-search are surprising.)

7. **`create_user(None)`** (F-10 / TS-002): the manager raises the model's
   username validation error instead of an opaque TypeError; the deferral
   xfail becomes a passing test. Internal-manager behavior; no spec delta
   (not observable through any capability surface).

8. **Byte-exact passwords owned by the spec** (F-09 / TS-001): the
   `trim_whitespace=False` behavior of the auth serializers becomes a
   user-accounts scenario instead of a test pinning unowned behavior.

9. **POST-only logout owned by the spec** (F-09 / TS-001): same pattern for
   the 405 logout behavior.

10. **Caption whitespace normalization owned by the spec** (F-09 /
    TS-001): DRF's `trim_whitespace` on the posts caption fields becomes a
    posts scenario ("Whitespace-only caption becomes empty").

11. **Admin and seed stay dev tooling** (F-11, F-12): Django admin surfaces
    remain out of the spec contract (reference-lineage decision, re-recorded
    here); `seed_demo_data` remains owned by the `config.yaml` context
    claim, which is now true. No spec deltas for either.

12. **config.yaml Django wording** (F-08): direct edit "Django 5+" →
    "Django 6+" (matches the Django 6.0.10 runtime). Not app behavior; no
    delta.

## Validation boundaries

- HTTP request format at the edge (views/serializers): caption whitespace
  trimming, serializer media-count 400, byte-exact credential fields.
- Application rules in use cases/services: follow race translation, search
  escaping, feed ordering.
- Business invariants in models: caption length, media count, username
  format (save AND bulk paths), deterministic ordering.
- Technical constraints in the database: existing unique/check constraints
  unchanged.

## Risks / Trade-offs

- The bulk-write queryset override touches the accounts layer used by every
  flow; the full suite guards regressions.
- Escaping the search input changes matching for queries that previously
  contained `%`/`_`; no legitimate workflow relies on wildcard search.
- Changing `Post.Meta.ordering` may affect tests that pin order with equal
  timestamps; the tiebreaker makes such order deterministic (`-id`), and
  tests setting `created_at` explicitly are unaffected.
