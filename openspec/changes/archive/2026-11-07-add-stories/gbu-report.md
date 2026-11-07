# GBU Report — add-stories (cycle 1)

## Loop outcome

| Group | Tasks | Good | Ugly | Iterations |
|-------|-------|------|------|------------|
| 1 | Models + migration (1.1, 1.2) | COMPLETED | APPROVED | 1 |
| 2 | StoryService + tests (2.1, 2.2) | COMPLETED | APPROVED | 1 |
| 3 | Use cases (3.1, 3.2) | COMPLETED | APPROVED | 1 |
| 4 | Web layer (4.1–4.4) | COMPLETED | APPROVED | 1 |
| 5 | Seed + cleanup command (5.1, 5.2) | COMPLETED | APPROVED | 1 |
| 6 | Quality gates (6.1) | gates green | — | — |

Bad (iteration 1): **SURVIVES** — 12 attack vectors, no blocking bugs.
Budget: 6/6 pytest runs used, ~11 min wall clock (over the 6-minute budget,
reported honestly by the agent; no budget extensions requested).

## Bugs and fixes during the cycle

- No product blocking bugs found. The Good iterations needed only
  orchestrator-level polish: two mypy `union-attr` fixes in new tests
  (asserting `image.name is not None` before `endswith`) and one positional
  assertion (stories bar renders above the post grid) closing Ugly's WEAK
  note on group 4.
- Bad's four "green-by-inspection" regression tests were re-executed by the
  orchestrator: one failed for a real harness reason (CSS class definition
  in the `<style>` block matched a negative `in body` assertion — fixed to
  assert the used class form `story-avatar story-avatar-viewed`), three
  ruff E501s reformatted. The thread-race test flaked on SQLite table locks
  (`OperationalError` under thread contention): the test now tolerates
  SQLite lock noise while still failing on any real exception
  (`IntegrityError` etc.) and pins "no duplicate rows" via the unique
  constraint. 8/8 consecutive stable runs confirmed.

## Bad attack summary (12 vectors)

Expiry exact-boundary consistency, purge cascade, `get_or_create` thread
race, web idempotency, ordering inversion (older-unviewed vs newer-viewed
group), ring state for older-story views, web rule rejections
(self/non-followed/expired/unknown), method/auth guards, payload injection
on create (owner/expires_at/media_type/QUERY_STRING ignored), non-followed
bar exclusion, exact +24h expiry. Not attacked (budget): DST transitions
(UTC fixed), seed re-run with pre-existing stories, `save(update_fields=...)`
misuses (no internal caller), uppercase UUID route (code-read only),
API story endpoints (none exist per spec).

## Non-blocking observations (accepted-open)

1. `StoryService.cleanup_expired` reports a pre-delete count; a story
   expiring between `count()` and `delete()` makes the reported number
   overstate deletions by one in a tiny race window (MEDIUM, report-only
   accuracy at demo scale; no spec requirement violated).
2. Uppercase UUIDs 404 at the route converter instead of the use-case
   "Story not found" toast (spec-silent; consistent not-found semantics).
3. Placeholder filename entropy 2^24 with Django storage collision suffix
   (no actual collision bug).

## Final gates

pytest 453 passed / 0 failed (2 pre-existing xfails retained) · coverage
99.45% (gate >= 80%) · ruff check + format clean · mypy clean (86 files) ·
`makemigrations --check` clean.

## Manual validation pointers (PAUSE-1)

- `.venv/bin/python manage.py seed_demo_data` then log in as
  `demoalice`/`demopass123` (or any seeded user): stories bar above the
  feed with "Your story" plus followed-user avatars (unviewed ring first).
- Create a story with the "Your story" button → "Story created" toast,
  bar re-renders.
- View a followed user's story by clicking their avatar → "Story viewed"
  toast, ring flips to viewed, group moves below unviewed groups.
- `cleanup_expired_stories` prints `Deleted N expired stories.`
