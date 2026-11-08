# Proposal — 07-resolve-cycle6-findings

## Why

The cycle-6 audit returned LIGHT DRIFT with five new low findings
(C6-01..C6-05) and one open process question (W-2). All five are
declare-or-tweak items; resolving them in one mini change brings the next
audit to IN SYNC literal.

## What Changes

- user-accounts "API JWT login": declare the login-side username trimming
  leniency (C6-01) and the session-cookie fallback accepted on API
  endpoints, which keeps the browsable `/docs/` working without a token
  (C6-04).
- user-accounts "API registration": declare the API email whitespace
  trimming (storage and uniqueness stay byte-exact thereafter) (C6-02).
- Tests: rename six sibling-named tests to their exact scenario names so
  the config traceability rule holds literally (C6-03).
- config: acknowledge the shipped story-ring accent gradient in the
  frontend target line (C6-05) and declare that API endpoints also accept
  session auth (C6-04 config side).
- workflow: amend the GBU budget policy to state that every test-runner
  execution counts toward the budget, including Bad's inspection runs
  (W-2 — declared default decision, reversible at PAUSE-1).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `user-accounts`: API registration (+1 scenario), API JWT login
  (+2 scenarios).

## Impact

- Two delta requirements, three new scenarios, three tests renamed, two
  config.yaml lines, one workflow.md policy paragraph. No production code
  changes; no endpoint or behavior changes.

## Business Decisions

| Date       | Decision                                                                                                          |
| ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 2026-11-08 | C6-01: the API login trims the username before authentication (behaviorally inert — no path can store a padded username); declared, not "fixed". |
| 2026-11-08 | C6-02: the API registration trims email whitespace before validation/storage; storage and uniqueness stay byte-exact. |
| 2026-11-08 | C6-04: API endpoints keep accepting session-cookie auth alongside JWT (it is what keeps /docs/ browsable); declared in config and specs. |
| 2026-11-08 | C6-05: the shipped story-ring gradient is acknowledged in the config target line rather than stripped.             |
| 2026-11-08 | W-2: every test-runner execution counts toward Bad's 6-run budget, including inspection runs; overruns are reported honestly. |
