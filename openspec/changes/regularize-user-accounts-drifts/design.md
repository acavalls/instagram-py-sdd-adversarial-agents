# Design

## Context

Post-archive regularization of the first change. The audit (2026-11-06,
DRIFT-001 … DRIFT-012) found only spec-silent behavior and two
under-enforcement gaps; the codebase is the user-accounts slice implemented
by `add-user-accounts` (archived). The living spec is
`openspec/specs/user-accounts/spec.md`.

## Goals / Non-Goals

**Goals:**

- Make the living spec describe the surfaces that exist by design (schema/
  docs, feed placeholder, token lifetimes, concurrency guarantee).
- Close the two under-enforcement gaps (username rule at model level; 401
  on every API login failure).
- Align credential handling across paths (no password trimming).
- Make logout CSRF-protected POST per Django's recommendation.

**Non-Goals:**

- `seed_demo_data` implementation (future work, no scenario needs it).
- Media/upload spec (owned by the change that first delivers uploads).
- Removing the admin site.
- Any new dependency.

## Decisions

1. **Username alphanumeric rule at model level.** Replace
   `AbstractUser.username_validator` (permissive `@/./+/-/_`) with an
   alphanumeric `RegexValidator` on `User.username_validator`, regenerate
   the validator into migration `0002`. Admin, shell and any future creation
   path then enforce the spec rule. Alternative: only fix the admin form —
   rejected, leaves other paths open.

2. **401 on every API login failure.** `LoginAPIView` maps serializer
   validation failure (blank/missing fields) to the same 401 generic error
   as wrong credentials. Alternative: keep 400 field errors — rejected, the
   requirement's literal wording ("On any failure … 401") wins and the
   generic error already guarantees no cause leak.

3. **No password trimming anywhere.** `trim_whitespace=False` on the
   password fields of `LoginSerializer` and `UserCreateSerializer`. The web
   path never trimmed; API now matches, so credentials are byte-exact.

4. **POST-only logout.** The logout view requires POST with CSRF; tests
   switch to `client.post`. No spec text change needed (the spec never
   mandated a method).

5. **Spec additions are descriptive, not behavioral rewrites.** The two
   ADDED requirements (API documentation surface, authenticated landing
   placeholder) describe surfaces that already exist and are tested; the
   MODIFIED requirements only add the concurrency guarantee, the token
   lifetimes and the blank-fields scenario.

## Risks / Trade-offs

- [Model validator migration changes a core field] → Additive validator
  change only; existing data (alphanumeric test usernames) unaffected;
  `makemigrations --check` clean after regenerating.
- [401-on-blank hides field feedback from API clients] → Intentional: the
  generic-error rule is the spec's stated anti-enumeration stance.

## Migration Plan

One Django migration (`accounts.0002_alter_user_username`) plus code/test
edits; rollback is trivial.

## Open Questions

None.
