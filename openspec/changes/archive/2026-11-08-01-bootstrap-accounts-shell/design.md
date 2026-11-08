# Design

## Context

Greenfield package: the clone repository has no Django project yet. The
fixed stack and Clean Architecture layering (views → use_cases → services →
models) come from the project's `openspec/config.yaml` and are not
renegotiated here. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Ship the accounts slice AND a minimal exercisable shell in one change, so
  the project is manually validable from the start.
- Make every spec scenario traceable to a pytest test named after it.
- Wire dual authentication end to end: Django sessions for the web UI, JWT
  for the API.

**Non-Goals:**

- Posts, follows, feed content, stories, suggestions (packages 02–04).
- Password reset, email verification, OAuth, profile editing.
- Production hardening (real SMTP, rate limiting, HTTPS configuration).

## Decisions

1. **Single custom user model from the start** (`accounts.User` extending
   `AbstractUser`, UUID primary key, unique email, bio, profile_pic).
   Alternative considered: default Django `User` plus a profile model —
   rejected because later migrations would be painful; `AUTH_USER_MODEL`
   is set on day one, before the first migration.

2. **Registration validation in two places, same rules.** Field-format
   rules (email shape, username length/alphanumeric, password min length 8)
   live in the write serializer for the API and are checked in the web view
   before calling the use case; identity-duplicate rules live in model
   validation used by the use case (`User.validate_registration`).

3. **JWT via `djangorestframework-simplejwt` defaults** (access 30 min /
   refresh 1 day, HS256, `Bearer` header). No new dependency beyond the
   fixed stack.

4. **Session auth via `django.contrib.auth`** (`authenticate`/`login`/
   `logout`) with `LOGIN_URL = /web/login/` and the feed as landing.

5. **The shell ships in this package, with declared placeholders.** The
   sidebar template renders all entries from day one; entries whose
   capabilities do not exist yet are anchor-less placeholder links pinned by
   the scenario "Placeholder entries have no destination". This is the
   minimal-wiring rule in action: later packages modify the same
   requirement instead of introducing navigation after the fact.

6. **Landing placeholder declared.** `/web/feed/` requires login and shows
   a placeholder empty state until the social capability delivers the
   followed-users feed; the placeholder is scenario-pinned so its
   replacement is a tracked observable change.

7. **Errors as explicit strings in use case outputs** (success/error
   dataclasses). Tests per scenario, named after it; `apps/accounts/tests/`
   plus web view tests.

## Dependency-wiring map

| Capability (this package) | Depends on | Not yet implemented? | Minimal wiring planned |
| ------------------------- | ---------- | -------------------- | ---------------------- |
| Web session auth          | Landing page | Yes (feed content) | `/web/feed/` renders a declared placeholder empty state; replaced by package 03 |
| Sidebar navigation        | Posts (Create), Profile page, Search/Explore/Messages/Notifications | Yes (all except Home/logout) | Entries rendered as placeholder links without destination; scenario-pinned. Create wired by package 02, Profile by package 03; the other four remain declared placeholders |
| API docs                  | Registered endpoints | Partially (only auth) | Schema lists the auth operations now; posts paths added by package 02 (MODIFIED delta) |

## Risks / Trade-offs

- [Two validation locations can drift] → Registration rules are pinned by
  scenarios in the spec; both paths are covered by tests.
- [Placeholder entries could be forgotten] → Each placeholder is
  scenario-pinned; replacing one requires its own delta, so the gap is
  visible at audit time.
- [JWT refresh endpoint is framework magic] → Covered by an explicit
  scenario/test so behavior is contractual, not incidental.

## Migration Plan

Initial Django project scaffold (`config/`, settings split base/local/test/
production, `AUTH_USER_MODEL` set before the first migration) plus the
accounts/web apps. Rollback is trivial: the change is additive and
self-contained.

## Open Questions

None.
