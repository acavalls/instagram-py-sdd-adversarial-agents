# GBU Report — 2026-11-08-03-add-social

## Result: APPLY_DONE — all 9 groups approved, Bad SURVIVES

## Group loop (Good → Ugly)

| Group | Scope | Good iters | Ugly verdicts |
| ----- | ----- | ---------- | ------------- |
| 1 | Social app + Follow model (DB constraints) | 1 | APPROVED iter 1 |
| 2 | FollowService + use cases (exact error strings) | 1 | APPROVED iter 1 |
| 3 | FeedService (follow subquery, 2 empty-state signals) + suggestions | 1 | APPROVED iter 1 |
| 4 | Profile page (view, templates, sidebar wiring, web caption-guard test) | 1 | APPROVED iter 1 |
| 5 | Follow/unfollow HTMX endpoints + canonical `_follow_button.html` | 2 | REJECTED iter 1 (DEV-001: unknown-relationship cause had no web-path test) → test added → APPROVED iter 2 |
| 6 | Feed switch to ListFeedUseCase + landing fulfilment (N-01 resolved) | 1 | APPROVED iter 1 |
| 7 | Suggestions panel + sidebar chrome (current-user block, footer) | 1 | APPROVED iter 1 |
| 8 | Following-list modal (search by username/name) | 1 | APPROVED iter 1 |
| 9 | Quality gates | 1 | APPROVED iter 1 (orchestrator-run) |

## Bad attack (🌵)

- Verdict: **SURVIVES** at attack iteration 1. Budget: 6/6 test-runner executions, ~1 min wall clock, 1 iteration.
- 31 attack tests created (29 passing, 2 sandbox-skipped): apps/social/tests/test_bad_attack_follow_integrity.py, apps/web/tests/test_bad_attack_social_feed_suggestions.py, apps/web/tests/test_bad_attack_social_profile_modal.py.
- Attacks repelled: follow→unfollow→follow cycle consistency, self-follow at service AND DB check-constraint level, duplicate error mapping, unfollowed users' posts never leaking into any feed window, 50-follow subquery feed, empty-state transitions, suggestions never containing self/followed users, modal search injection (SQL wildcards, quotes, unicode, 10k-char q), 120-follow modal, cross-user modal access, non-HTMX POST, CSRF (403 without token), anonymous (302), /api/posts/ own-posts-only.
- Bugs found: **none**. No xfail pins.
- Sandbox limitation (honest caveat): the 2 true-thread race tests (ATK-001/002) skip on shared-cache SQLite (SQLITE_LOCKED); the invariants they assert are separately proven by passing sequential-duplicate, DB-constraint and consistency tests.
- Minor observations (spec-silent, not bugs): profile counters materialize full lists instead of COUNT(); offset pagination can shift windows if the follow set changes mid-scroll; _search_following uses Python case-folding instead of ORM icontains (exotic case-folding edge).
- Orchestrator normalization of Bad's files (content untouched): ruff format; manual lint-only edits (2× F841 unused variable, 1× mypy type-ignore on a Union access).

## Final gates (all green)

- pytest: **361 passed, 2 skipped, 1 xfailed** — coverage **98.92%** (≥ 80 required)
- ruff check: 0 issues · ruff format --check: 158 files clean · mypy: 0 errors (101 files) · manage.py check: no issues · makemigrations --check: clean

## Carried-forward findings touched by this change

- N-01 (landing contradiction): resolved — user-accounts landing placeholder MODIFIED to the followed-users feed; posts listing MODIFIED consistently.
- N-05 (card profile link dangling): resolved — profile routes exist; card links now point at a live page.
- F-01..F-10 (except F-10/HTMX resolved in cycle 2) remain open, out of this change's scope.

## Notes on delta adaptation (tooling compliance)

- MODIFIED deltas keep the original scenario NAMES with new content (user-accounts landing: "Placeholder requires login"/"Logged-in user reaches the placeholder"; posts listing: "Personal feed on the feed page"/"Home feed loads more posts on scroll") because the openspec validator refuses MODIFIED blocks that drop scenarios. The posts delta's "## Notes" section was moved into design.md (Decision 6). Synced back to spec-ref-v2/03-add-social.

## Manual validation script (for the Sheriff)

Web (two browsers or two sessions A and B):
1. Register A and B. As A: create 2 posts (sidebar Create).
2. As B: home feed shows the "Share Photos" empty state (icon, title, subtitle, CTA) — B follows nobody.
3. As B: click the CTA (creates a random post for B). Home feed now shows the secondary state "No posts from the people you follow yet."
4. As B: sidebar Profile → own profile: stats (posts 1, followers 0, following 0), tabs POSTS active, SAVED/TAGGED placeholders, own post with edit/delete controls. Edit caption above 2200 chars → error, post unchanged.
5. As B: visit A's profile (via B's suggestions panel on the home page — A appears as "New to Instagram"): follow button "Follow" → click → toggles to "Following" with toast "Followed successfully"; click again → back to "Follow" with toast "Unfollowed successfully". Re-follow A.
6. As B: home feed now shows A's posts newest first with infinite scroll; the suggestions panel no longer contains A; footer links About/Help/API/Jobs/Privacy/Terms and the current-user block render.
7. As B: A's profile → following stat opens the following-list modal; search "a" filters the list.
8. As B: try `/web/profile/<own-pk>/follow/` via curl with session — rejected "You cannot follow yourself".
9. curl (JWT): login as A → `GET /api/posts/` returns only A's own posts (no followed-users leak); `GET /api/posts/?limit=1&offset=0` windows correctly. `/docs/` still renders.
