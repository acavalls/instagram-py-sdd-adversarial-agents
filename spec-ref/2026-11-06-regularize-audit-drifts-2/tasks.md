# Tasks

## 1. C1 — expired stories not viewable

- [x] 1.1 Add the expiry check to `ViewStoryUseCase` (after existence, before self-view): reject with "Story has expired" when `expires_at` has passed
- [x] 1.2 Add use-case test `test_rejects_expired_story` and web test `test_expired_story_not_viewable` traceable to the "Expired story not viewable" scenario

## 2. C2 — not-found toast documented and traceable

- [x] 2.1 Rename `test_unknown_story_rejected` to `test_unknown_story_reported_as_not_found` (docstring "Scenario: Unknown story reported as not found")

## 3. T1 — admin-console scenario test

- [x] 3.1 Add staff test in `apps/accounts/tests/` (`test_staff_manages_domain_models`) asserting the `/admin/` changelists for User, Post, Follow and Story

## 4. Quality gates

- [x] 4.1 Run full pytest suite (all pass) and coverage (>= 80%)
- [x] 4.2 Run ruff and mypy clean

## Workflow follow-up

- Commit implementation (user performs the commit at the gate)
- Verify the change (`/opsx-verify`)
- Archive the change (`/opsx-archive`)
