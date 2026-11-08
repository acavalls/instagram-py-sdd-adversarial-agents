# Design

## Context

Cycle 6 resolved all 19 carried findings; the audit found five new low
items, all declare-or-rename work, plus the W-2 policy question. This mini
change is documentation-first: no production code changes, only one delta
capability (user-accounts), test renames and two doc files.

## Goals / Non-Goals

**Goals:**

- Next audit returns IN SYNC literal: every declared behavior tested and
  traceable by scenario name; config claims accurate.

**Non-Goals:**

- Any behavior change (the declared leniencies are the implemented ones).
- Restricting API auth to JWT-only (would break browsable /docs/).

## Decisions

1. **Declare, don't change** (C6-01, C6-02): both trims are behaviorally
   inert or consistent with existing declared patterns (the caption-trim
   precedent); declaring is cheaper and safer than touching auth paths.
2. **Session fallback stays** (C6-04): it is what keeps `/docs/` usable
   without a token; declared in config principle 4 and as a user-accounts
   scenario.
3. **W-2 policy default**: every test-runner execution counts toward the
   6-run budget; overruns reported honestly (matches cycles 4-6 practice).

## Risks / Trade-offs

- [Declaring trimming leniencies could read as blessing sloppiness] → Both
  declarations state what the code does and why it is inert (no padded
  username can exist in storage; email storage stays byte-exact).
- [Renaming tests can lose history] → git mv semantics; assertions and
  coverage unchanged, verified by the suite.

## Open Questions

None.
