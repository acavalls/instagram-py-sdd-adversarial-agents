# Design

## Context

Greenfield change: the clone repository has no Django project yet. The
reference implementation lives in `/home/ale/mapfre/personal/django_ig`
(`apps/accounts`, `apps/web`, `config/settings`). The fixed stack and Clean
Architecture layering come from `openspec/config.yaml` and are not
renegotiated here. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Recreate the reference `accounts` + web auth slice with Clean Architecture
  layering: views → use_cases → services → models.
- Make every spec scenario traceable to a pytest test named after it.
- Wire dual authentication end to end: Django sessions for the web UI, JWT
  for the API.

**Non-Goals:**

- Posts, follows, feed, stories, suggestions (later changes).
- Password reset, email verification, OAuth, profile editing.
- Production hardening (real SMTP, rate limiting, HTTPS configuration).

## Decisions

1. **Single custom user model from the start** (`accounts.User` extending
   `AbstractUser`, UUID primary key, unique email, bio, profile_pic).
   Alternative considered: default Django `User` plus a profile model —
   rejected because migrations later would be painful; the reference app
   sets `AUTH_USER_MODEL` on day one.

2. **Registration validation in two places, same rules.** Field-format rules
   (email shape, username length/alphanumeric, password min length 8) live in
   the write serializer for the API and are checked in the web view before
   calling the use case; identity-duplicate rules (unique email/username)
   live in the model validation used by the use case
   (`User.validate_registration`). Alternative considered: pushing all rules
   into the use case — rejected as over-engineering for this clone; the
   reference app does exactly the split above and we mirror it.

3. **JWT via `djangorestframework-simplejwt` defaults** for login response
   (`RefreshToken.for_user`) and the refresh endpoint; lifetimes 30 min
   access / 1 day refresh, HS256, `Bearer` header, `user_id` claim mapped to
   the UUID primary key. No new dependency beyond the fixed stack.

4. **Session auth via `django.contrib.auth`** (`authenticate`/`login`/
   `logout`) with `LOGIN_URL = /web/login/` and feed redirects, exactly as
   the reference app. Alternative considered: a custom session layer —
   rejected, no benefit.

5. **Views stay thin.** Web views read form fields, invoke use cases and
   render templates; API views validate with serializers, invoke use cases
   and shape responses. Business rules (duplicates, generic auth error)
   live in use cases/model — never in views.

6. **Errors as explicit strings in use case outputs**, matching the reference
   dataclass pattern (`success`, `error`). Simpler than an exception ladder
   for a learning clone.

7. **Tests per scenario, named after it.** Suite layout mirrors the
   reference: `apps/accounts/tests/` (models, services, use cases, views)
   plus web auth view tests, with `factories.py` using factory_boy. pytest
   with `DJANGO_SETTINGS_MODULE=config.settings.test`, coverage >= 80%.

## Risks / Trade-offs

- [Two validation locations can drift] → Registration rules are pinned by
  scenarios in the spec; both paths are covered by tests.
- [JWT refresh endpoint is framework magic] → Covered by an explicit
  scenario/test so behavior is contractual, not incidental.
- [Username uniqueness is case-sensitive like the reference] → Accepted for
  parity; a future change may add case-insensitive uniqueness.

## Migration Plan

Initial Django project scaffold (`config/`, settings split base/local/test/
production, `AUTH_USER_MODEL` set before the first migration) plus the
accounts/web apps. Rollback is trivial: the change is additive and
self-contained.

## Open Questions

None.
