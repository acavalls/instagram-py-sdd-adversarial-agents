# GBU Report — 2026-11-08-04-add-stories

## Result: APPLY_DONE — all 5 groups approved, Bad SURVIVES

## Group loop (Good → Ugly)

| Group | Scope | Good iters | Ugly verdicts |
| ----- | ----- | ---------- | ------------- |
| 1 | Story/StoryView models (24h invariant on the save path) + migration | 1 | APPROVED iter 1 |
| 2 | StoryService + CreateStory/ListFeedStories/ViewStory use cases | 1 | APPROVED iter 1 |
| 3 | Web surface: create/view endpoints, stories bar partial, OOB toasts, ring CSS | 1 | APPROVED iter 1 |
| 4 | Lazy purge on home render + management command + bar-above-posts wiring | 1 | APPROVED iter 1 |
| 5 | Quality gates | 1 | APPROVED iter 1 (orchestrator-run) |

## Bad attack (🌵)

- Verdict: **SURVIVES** at attack iteration 1. Budget: ~5/6 minutes, **7/6 test-runner executions** (over by one — two were single-test inspection runs of Bad's own fixture mistakes, all targeted, never full-suite; reported honestly), 1 iteration.
- 25 attack tests created: apps/posts/tests/test_bad_attack_story_invariants.py (8), apps/web/tests/test_bad_attack_story_endpoints.py (17).
- Attacks repelled: re-save with tampered expiry, ±1s boundary (exact +24h accepted), ORM round-trip lifetime stability, active-filter boundary (==now expired, +1s active), CSRF-less/anonymous/GET attacks (403/302/405), malformed and unknown uuid handling, expired/own/non-followed story views rejected with exact texts and no records, 5× duplicate view POSTs → one row, smuggled non-followed story invisible in bar and unviewable, viewer's own story renders no group avatar (only "Your story"), 100-story group → one avatar newest-first, unviewed-first ordering with ring flip, purge keeps active stories and their views, command idempotency (1 then 0), purge during feed render does not break pagination.
- Bugs found: **none**. No xfail pins.
- Minor observations (spec-silent, not bugs): ORM-only expiry bypass via queryset.update()/bulk_create (spec scopes the rule to the save path; not web-reachable); malformed uuid path segment 404s at the URL converter instead of a 200 "Story not found" toast (spec-ambiguous, safe); story endpoints' OOB bar re-renders do not lazy-purge (spec mandates purge only on home render; the active filter hides expired stories anyway); concurrent get_or_create race not demonstrable on SQLite (NOT_FEASIBLE_IN_SANDBOX).
- Orchestrator normalization of Bad's files (content untouched): ruff format + check --fix (no changes needed, already clean).

## Final gates (all green)

- pytest: **423 passed, 2 skipped, 1 xfailed** — coverage **99.02%** (≥ 80 required)
- ruff check: 0 issues · ruff format --check: 182 files clean · mypy: 0 errors (117 files) · manage.py check: no issues · makemigrations --check: clean

## Notes on delta adaptation (tooling compliance)

- The posts MODIFIED delta keeps the living-spec scenario names ("Personal feed on the feed page", "Home feed loads more posts on scroll") with the stories-bar content, per the openspec validator constraint; synced to spec-ref-v2/04-add-stories.

## Manual validation script (for the Sheriff)

Web (two browsers or two sessions A and B):
1. Register A and B; B follows A (via suggestions on the home page).
2. As A: click "Your story" on the home page → toast "Story created" and the bar refreshes out of band.
3. As B: home page shows the stories bar above the post list with A's avatar (unviewed ring); A appears (B follows A). A non-followed user's story never appears.
4. As B: click A's avatar → toast "Story viewed", ring updates to viewed on the OOB re-render; the group reorders behind any unviewed groups.
5. As B: click again → no duplicate view record (idempotent).
6. As B: attempt `POST /web/stories/<own-story-id>/view/` (create your own story first) → HTTP 200, error toast "You cannot view your own story", no view recorded.
7. Backdate a story's expires_at in the shell (`Story.objects.update(expires_at=...)`), load the home page → the story is gone from the bar and its records are deleted (lazy purge).
8. Run `.venv/bin/python manage.py cleanup_expired_stories` → reports "Deleted N expired stories."; run again → "Deleted 0 expired stories."
9. Anonymous POST to /web/stories/create/ → redirect to login; CSRF-less POST → 403.
