# Spec Audit — 2026-11-06 (post add-posts archive)

Verdict: LIGHT DRIFT (all findings low severity). Cycle closed with findings
documented here for a future regularization cycle. Full report in the cycle
conversation; summary below.

## Findings and recommended resolutions (none applied)

| ID | Type | Finding | Recommendation |
|----|------|---------|----------------|
| ENV-001 | ENVIRONMENT | `openspec/config.yaml` promises a `seed_demo_data` management command; it does not exist yet | (c) business decision: confirm whether it is a pending future cycle or reword config.yaml |
| CS-001 | CODE→SPEC | 10-media cap enforced only in the API serializer; `PostService.create` accepts any number of files | (b) fix code: model/service-level count guard mirroring the caption save-guard |
| CS-002 | CODE→SPEC | Post ordering is `-created_at` only, no tiebreaker; pagination window stability relies on SQLite tie order | (b) fix code: add a deterministic tiebreaker (e.g. `id`) to Post ordering |
| CS-003 | CODE→SPEC | Web post card renders only the first media of a multi-media post | (c) business decision: single image vs carousel on the feed card; land as a small spec clarification |
| CS-004 | CODE→SPEC | `queryset.update()`/`bulk_create` bypass the model-level username rule (documented deferral, unreachable from endpoints) | (b) fix in a future regularization cycle |
| TS-001 | TESTS | POST-only logout (405), byte-exact passwords, API whitespace-caption normalization are pinned by tests but absent from living specs | (a) update specs via a regularization change so tests do not pin unowned behavior |
| TS-002 | TESTS | xfail BUG-005 (`create_user(None)` TypeError) exists only as an executable deferral record | (b) fix in a future cycle; keep the xfail until scheduled |

## Coverage at close

- user-accounts: 23/23 scenarios with a traceable test.
- posts: 18/18 scenarios with a traceable test.
- Gates: pytest 259 passed / 2 xfailed, coverage 99.42%, ruff 0 issues, mypy 0 errors.

## Not verified

Browser-level UX (HTMX swaps, toasts, CDN assets), true multi-process
concurrency, production settings execution, live media rendering.
