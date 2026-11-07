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
   earlier, friendlier 400. `PostMedia`'s queryset additionally overrides
   `bulk_create()` with the same pre-insert per-post count check (Bad
   BUG-R001, 2026-11-07): rows beyond the 10-file limit are never written,
   so the invariant also holds on bulk inserts. The same queryset now also
   overrides `update()` and `bulk_update()` so a media row cannot be
   reassigned onto a post without room (Bad BUG-R003, 2026-11-07):
   `update()` touching `post`/`post_id` verifies per-target capacity for
   the reassigned rows and — when the target post would exceed
   `MEDIA_MAX_COUNT` — refuses the whole write silently (returns 0; a
   single UPDATE cannot apply partially); `bulk_update()` applies the same
   per-target accounting row by row and never writes a reassigned row that
   would exceed the target's capacity, mirroring the `bulk_create()`
   store-only-what-fits semantics. The repro tests pin silent refusal (no
   exception), so unlike the username guard these refusals do not raise;
   the invariant ("up to 10 ordered files attached to a post") is what the
   delta scenario requires, and it holds either way.

4. **Username rule on bulk writes** (F-04 / CS-004): a custom `User`
   queryset overrides `update()`, `bulk_create()` and `bulk_update()` to
   run the same
   username-format validation as `save()`. Literal values that break the
   rule raise the model's username `ValidationError`. Non-literal values
   (e.g. `F()`/`Combinable` expressions) have no text to validate, so the
   write that carries them is rejected with the model's username
   `ValidationError` (orchestrator adjudication on Bad BUG-R002,
   2026-11-07: the delta scenario requires rejection with a validation
   error, not a silent refusal) instead of persisting an unvalidated
   username; the whole `update()` call writes nothing. Literal invalid
   strings behave as before. The xfail documenting
   the bypass becomes a passing test. `bulk_update()` validates every
   object's username in memory before the batched CASE-WHEN write (Bad
   BUG-R018, 2026-11-07), so one violating object refuses the whole batch
   atomically and the DB keeps the old usernames.
   (agent-decided 2026-11-07; non-literal refusal contract added after the
   Bad attack round 1, upgraded to a raising contract after adjudication)

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

13. **Caption limit on `Post.objects.update()`** (Bad BUG-R004,
    2026-11-07): a custom `PostQuerySet` (exposed as the default manager
    via the same `from_queryset` idiom as `UserManager`) overrides
    `update()` so a write that carries a `caption` cannot store an
    over-limit value: a literal string longer than 2200 characters and a
    non-literal expression (e.g. `F()`/`Combinable`, which has no text to
    validate) both refuse the whole `update()` call, which writes nothing.
    The repro test pins silent refusal (no exception), so the refusal
    returns 0 instead of raising the model's caption `ValidationError`;
    the delta scenario ("Caption length limit": an update with a longer
    caption is rejected) is satisfied by the caption never being stored.
    Existing legitimate `Post.objects.update()` calls (test seeding of
    `created_at`) are unaffected. The same queryset now also overrides
    `bulk_create()` (Bad BUG-R005, 2026-11-07) so the batched INSERT cannot
    persist an over-limit caption either: over-limit literal captions are
    dropped from the batch (mirroring the `PostMediaQuerySet.bulk_create`
    store-only-what-fits semantics) and a non-literal caption expression is
    refused with the model's caption `ValidationError`.

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
