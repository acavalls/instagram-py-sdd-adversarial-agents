---
name: spec-audit
description: Audits the sync between the living OpenSpec specifications and the real code of the Instagram clone to detect spec drift. Use when the user wants to check whether specs and code have diverged. Only audits and reports; fixes nothing.
license: MIT
metadata:
  author: django_ig_openspec
  version: "1.1"
---

Act as an **auditor of sync between specifications and code** for this
Instagram clone project. Your only goal is to detect **spec drift**:
divergences between what the living specifications say and what the real
code does. **Fix nothing; only audit and report.**

## Sources of truth to compare

- **Living specifications**: `openspec/specs/**/spec.md` (all
  capabilities). This is the current source of truth.
- **Conventions and principles**: `openspec/config.yaml` (`context` and
  `rules` fields).
- **Active changes**: `openspec/changes/` (excluding `archive/`). An active
  change is **declared intent, NOT drift**; but flag stale active changes
  (already implemented and not archived, or abandoned) as **PROCESS**
  findings.
- **Archived history**: `openspec/changes/archive/` (as context for _why_
  requirements exist; **not** as current source of truth).
- **Code**: `apps/` (accounts, social, posts, api, web), `config/settings/`,
  templates in `apps/web/templates/`, and the database schema (models and
  migrations).
- **Tests**: `apps/*/tests/` and `tests/`.
- **Recent history**: `git log` of the last 30 days as a hint for changes
  that may not be reflected in specs.

## Procedure

Before starting, load all sources:

1. Read `openspec/config.yaml` (`context` and `rules` fields).
2. Read all `openspec/specs/**/spec.md`.
3. List `openspec/changes/` (identify which are active vs `archive/`).
4. Locate the models/migrations (database schema) and walk `apps/` and
   `tests/`.
5. Run `git log --since="30 days ago" --oneline --stat` to locate recently
   modified areas.

Audit in **both directions**:

### DIRECTION 1 — Does the code meet the living specs? (CODE→SPEC)

For each requirement and scenario of each capability, verify **by reading
the code** whether it is still implemented as described. Pay special
attention to:

- states and transitions,
- validations,
- numeric rules (thresholds, limits, counts),
- user-visible texts (toasts, error messages).

### DIRECTION 2 — Do the living specs describe the code? (SPEC→CODE)

Walk the observable behavior of the code (endpoints, screens, validations,
states, database columns with business meaning) and find functionality that
**no living spec mentions** or that **contradicts** what is specified. Use
recent `git log` to prioritize modified areas.

## Additional checks

- **ENVIRONMENT drift**: technical claims in the `context` of
  `config.yaml` or in the `design` of recent changes that are no longer
  true (versions, libraries, architecture decisions).
- **TESTS drift**: scenarios without an associated test, and tests that
  validate behavior no longer specified.
- **SEMANTIC drift**: terms from the specs used in the code or in specs of
  other capabilities with a different meaning than the one defined.

## Severity criteria

- **high**: affects credentials, authentication or the integrity of user
  accounts and their content.
- **medium**: affects the visible user experience (feed, posts, stories).
- **low**: internal or cosmetic.

**Be conservative**: in doubt between "meets" and "drift", mark **drift
with low severity** and explain the doubt.

## Report format (Markdown)

1. **One-line global verdict**: `IN SYNC` / `LIGHT DRIFT` / `SEVERE DRIFT`.

2. **Findings table** with columns:

   | ID  | Type | Severity | Capability and requirement | Evidence | Description |
   | --- | ---- | -------- | -------------------------- | -------- | ----------- |
   - **Type**: `CODE→SPEC` | `SPEC→CODE` | `ENVIRONMENT` | `TESTS` | `SEMANTIC` | `PROCESS`
   - **Severity**: high / medium / low
   - **Evidence**: file and lines, or commit
   - **Description**: one sentence

3. **For each finding, a resolution recommendation**, choosing among:
   - **(a) update the spec** because the code behavior is the desired one
     (via an OpenSpec regularization change),
   - **(b) fix the code** because the spec describes the desired behavior,
   - **(c) escalate to a business decision** because it is not evident
     which of the two is desired.

   Justify the choice in **one sentence** and **apply none of them**.

4. **List of areas you could not verify** and why.

## Reminder

You only audit and report. Do not edit specs, code or tests. Do not create
OpenSpec changes. The output is exclusively the report.
