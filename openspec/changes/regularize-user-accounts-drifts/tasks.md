# Tasks

## 1. Spec regularization deltas (DRIFT-001, 005, 008, 011)

- [ ] 1.1 Delta spec written with ADDED "API documentation surface" (schema + Swagger UI scenarios) and ADDED "Authenticated landing placeholder" (placeholder login-guard and reachability scenarios); verify `openspec validate regularize-user-accounts-drifts` passes
- [ ] 1.2 Delta spec MODIFIED "User registration" (storage uniqueness guarantee + "Concurrent duplicate registration keeps data consistent" scenario) and MODIFIED "API JWT login" (token lifetimes + "API login with missing fields" scenario); verify the MODIFIED blocks carry the full updated requirement content

## 2. Code regularization (DRIFT-002, 003, 004, 012)

- [ ] 2.1 Enforce the alphanumeric username rule at model level (`User.username_validator` alphanumeric RegexValidator) with migration `0002`; verify `manage.py makemigrations --check` clean and a test proves a non-alphanumeric username is rejected on direct model save (admin/shell path)
- [ ] 2.2 Make `LoginAPIView` answer 401 "Invalid credentials" for blank/missing fields too; verify a scenario-named test "API login with missing fields" passes and no other login behavior changes
- [ ] 2.3 Disable password whitespace-trimming in `LoginSerializer` and `UserCreateSerializer`; verify a test proves a password with surrounding spaces round-trips identically on API register + login and web login
- [ ] 2.4 Make logout CSRF-protected POST-only; verify the "Successful logout" test still passes using POST and a test proves GET logout no longer logs out

## 3. Regression and gates

- [ ] 3.1 Update any tests affected by the regularization (logout method, blank-login status, trimming) and keep every archived scenario test passing; run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green
- [ ] 3.2 Verify the OpenAPI schema still renders with register/login/refresh operations (schema test) after the changes

## Workflow follow-up

- Archive after verify; the deltas merge into `openspec/specs/user-accounts/spec.md`.
- Re-run the spec audit; expected verdict: IN SYNC.
