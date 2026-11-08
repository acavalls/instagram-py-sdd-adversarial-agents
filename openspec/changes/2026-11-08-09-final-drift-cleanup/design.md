# Design

## Context

Six low findings remain after cycle 8; every one is a declaration, a test
alias or a policy sentence. No production code changes.

## Goals / Non-Goals

**Goals:**

- Next audit returns IN SYNC literal: 140/140 scenarios traceable, no
  undeclared pinned behavior, policy text matching practice.

**Non-Goals:**

- Any behavior change (403-no-challenge, session precedence and footer
  scope are declared as implemented).
- Extending branding to Swagger/admin (separate surfaces by declaration).

## Decisions

1. **Declare the implemented auth semantics** (C7-02, C7-03): both are
   verified by attack tests and are the sane defaults; declaring costs one
   sentence + one scenario each.
2. **Scope the brand-naming text to reality** (C8-02, C8-03): footer
   declared feed-only; titles scenario scoped to the web UI.
3. **Policy follows practice** (C8-01): post-exhaustion orchestrator
   verification (full suite + Ugly) is declared, with honest reporting.

## Risks / Trade-offs

- [Declaring 403-no-challenge deviates from API convention] → It is what
  the declared authenticator order produces and what keeps /docs/
  coherent; changing it later is a one-line decision.

## Open Questions

None.
