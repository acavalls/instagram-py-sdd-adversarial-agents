# Design

## Context

All five spec-ref-v2 packages are implemented and archived. The five audit
reports converge on one pattern: the code is behaviorally sound and
test-pinned, but several contracts live only in tests, and four genuine
defects survive (N-05 broken card links, F-02 broken manager tooling, F-03
plain-text bulk passwords, F-01 missing declared bootstrap). This change
moves every uncontroversial contract into the living specs and fixes the
defects, so the next audit returns IN SYNC.

## Goals / Non-Goals

**Goals:**

- One coordinated regularization change; every new scenario scenario-named
  tested in the same change.
- Fix the four genuine defects without changing any specified user-visible
  flow except the declared regularizations.

**Non-Goals:**

- The W-2 process-policy decision (Bad budget semantics) — stays documented.
- Landing Google Fonts/gradients (visual work stays a config target).
- Any new capability or endpoint.

## Decisions

1. **Spec-first for pinned-only contracts** (F-04, F-09, N-04, N-06, W-1,
   C4-01, C4-02, C5-01, C5-02, S-02): the implemented behavior is the
   desired one; each gets a declaring scenario plus a scenario-named test.
2. **Code-first for defects** (N-05, F-02, F-03, F-01, S-01): the living
   spec (or config claim) already describes the right behavior; the code is
   brought up to it. F-01's bootstrap migration is DEBUG-guarded so
   production migrations never materialize a known credential.
3. **Consistency defaults for the two UX escalations** (F-05/F-07, F-06):
   padded usernames are rejected everywhere (the web already rejects; DRF
   trimming is removed); email uniqueness is byte-exact like the password
   rule. Both are declared as Business Decisions and are reversible at
   PAUSE-1.
4. **F-10** is a config.yaml wording fix (targets, not claims), not a spec
   delta.

## Migration Plan

One additive data migration (`accounts.0003`) that creates the dev
superuser `bob` only under `settings.DEBUG` and only if absent. Rollback:
delete the migration; the other changes are code/spec edits.

## Risks / Trade-offs

- [Regularizing a bypass (C4-02) reads as blessing a hole] → The declared
  contract explicitly scopes the 24h invariant to the save path and names
  the bulk paths as out of its scope, matching the stories spec's existing
  "MUST hold on the save path" wording; nothing new is allowed.
- [DEBUG-guarded migration smells] → It makes the config's long-ignored
  claim true for developers while production (DEBUG off) is untouched; the
  guard is pinned by a test that runs the migration function with DEBUG
  off and asserts no user is created.
- [Changing the API username rule] → Existing clients sending padded
  usernames get 400 instead of 201; no test or endpoint in the repo sends
  padded usernames except the probe being updated.

## Open Questions

None.
