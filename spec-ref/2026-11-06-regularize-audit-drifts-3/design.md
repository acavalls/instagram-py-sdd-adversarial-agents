# Design: regularize-audit-drifts-3

Pure regularization cycle from audit #6. No behavior changes.

## Decisions

1. **F1/F2/F3/F6 → spec update (a)**: the code states are reference parity
   behaviors already covered by tests; regularizing the spec is cheaper and
   keeps "spec is the source of truth" honest.
2. **F4 → spec update (a)**: non-HTMX GET with `?page=N` rendering the full
   page at window N is a sound progressive-enhancement contract; the
   archived design's "plain GET renders the first window" statement loses.
   The spec documents the actual (desired) behavior; code untouched.
3. **F5/F8 → test fixes (b)**: add the missing icon assertion and the
   missing scenario docstrings. No production code changes.
4. **F7 → config.yaml wording fix**: rename `seed_data` to
   `seed_demo_data` in `openspec/config.yaml`.
5. Agent decision (flagged): the sidebar footer links and current-user block
   are named in the `User suggestions` requirement text as panel chrome
   rather than split into a new web-ui requirement — they only render on the
   home feed sidebar today.

## Test plan

- F5: `test_empty_feed_state_shows_share_photos_call_to_action` gains an
  icon assertion (`empty-feed` / `bi-camera`).
- F8: scenario docstrings added to the 4 supplementary tests named in the
  audit (test_web_content.py:51,66; test_web_views.py(social):37,98).
- Full suite, coverage, ruff, mypy as usual gates.
