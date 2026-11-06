# Design

## Context

Audit #3 found four low-severity drifts after archiving `add-stories`. This is
a regularization change: it aligns code and specs without introducing new
features. See proposal.md for the finding-to-fix mapping.

## Goals / Non-Goals

- Goals: enforce the "active story" rule in the view-tracking path (C1),
  document the not-found toast (C2), normalize spec URL notation (S1), close
  the carried-over admin-console test gap (T1).
- Non-Goals: no new behavior beyond the two new view-tracking scenarios; no
  changes to creation, bar rendering, ordering or cleanup; no API endpoints.

## Decisions

1. **Expiry check in `ViewStoryUseCase`, ordered after existence and before
   self-view/follow checks** (C1). Rationale: the spec says "active story";
   checking expiry right after fetching the story keeps the error messages
   distinguishable ("Story has expired" vs "Story not found") and needs no
   DB change. A separate message avoids conflating expiry with not-found,
   which keeps the C2 scenario meaningful.

2. **C2 as a spec scenario, not code change**: the existing
   `test_unknown_story_rejected` test already exercises the behavior; it only
   needs its docstring renamed to the new scenario name
   ("Unknown story reported as not found") for traceability.

3. **S1 as a pure spec rewrite**: URLs in the stories living spec become
   `/web/stories/...` to match the `/web/profile/...` convention in the
   social spec. No code change (the routes already live under `/web/`).

4. **T1 as a staff-session test**: `client.force_login(staff_user)` +
   `GET /admin/` with `follow=True`, asserting the changelist headings for
   User, Post, Follow and Story render. Traceable to the admin-console
   scenario "Staff manages domain models".

## Risks / Trade-offs

- The expiry check makes the view use case depend on the clock like the rest
  of the story lifecycle; consistent with `get_feed_stories` and
  `cleanup_expired`, no new risk.
