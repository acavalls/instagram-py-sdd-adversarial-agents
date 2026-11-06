# Tasks: regularize-audit-drifts

## 1. Regularization tests and config fix (no production code changes)
- [x] 1.1 Test: topbar shows a Profile link to the logged-in user's own profile (scenario: Topbar links to own profile) (spec social: User profile page)
- [x] 1.2 Test: anonymous request to `/admin/` lands on the admin login page (scenario: Anonymous visitor redirected to admin login) (spec admin-console: Django admin console)
- [x] 1.3 Fix `openspec/config.yaml` context app list: "accounts, social, posts, api, web" → "accounts, posts, social, web" with a note that API endpoints live inside the domain apps (audit A3)
