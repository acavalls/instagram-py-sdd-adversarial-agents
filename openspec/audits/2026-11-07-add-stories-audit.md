# Spec Audit — 2026-11-07 (post add-stories archive)

Verdict: LIGHT DRIFT (2 low findings, both documentation/convention-level).
Cycle closed with the findings documented here for a future regularization
change. Stories: 15/15 scenarios traceable to passing tests; no regressions
in posts, social, user-accounts or api-docs; config.yaml claims verified;
archived deltas correctly synced into the living specs.

## Findings and recommended resolutions (none applied)

| ID | Type | Finding | Recommendation |
|----|------|---------|----------------|
| S-01 | CODE→SPEC | `Story.save()` only derives the 24h expiry when `expires_at` is empty; an explicit `expires_at` (or a future bulk path) persists any lifetime, unlike the enforced caption/media/username guard pattern. All system flows (use case, seed) set exactly `created_at + 24h`, so no scenario fails. The save docstring also overstates the guard. | (c) business decision: enforce the 24h lifetime on every persistence path (raising on explicit/illegal values, like the caption guard) or keep derive-only; a regularization change is the vehicle either way |
| S-02 | SPEC→CODE | The web view endpoint answers unknown/expired ids and self-view/non-followed rejections with HTTP 200 + error toasts ("Story not found", "You can only view stories from people you follow", "You cannot view your own story") and re-renders the bar; the spec fixes only "reports the error" for the self-view case and is silent about the other texts and the non-404 status. | (a) small stories delta owning the error texts and the 200-with-toast contract (matches the repo's established HTMX failure convention) |

## Carried-open context (accepted, do not re-report)

- N-01..N-05 from the 2026-11-07 regularize-social-drifts audit (bulk-path
  refusal contracts, legal bulk_update impossibility, vacuous r026 test,
  `first_image_url` ownership) remain accepted-open for a future cycle.
- OBS from the add-stories gbu-report: cleanup_expired count race window
  (MEDIUM, report-only), uppercase UUID route 404 (spec-silent), placeholder
  filename entropy (no bug).

## Coverage at close

- stories: 15 scenarios, posts: 19, user-accounts: 25, social: 16,
  api-docs: 2 — all with a traceable passing test.
- Gates: pytest 453 passed / 0 failed, coverage 99.44-99.50%, ruff clean,
  mypy clean, makemigrations --check clean.

## Not verified

Live browser rendering of the stories bar (CSS ring states, HTMX OOB swap);
`get_feed_stories` per-story `StoryView.exists()` N+1 beyond demo scale;
storage-file deletion on story purge (spec does not require it, matching the
posts capability precedent).
