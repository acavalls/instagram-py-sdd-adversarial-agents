# Spec Delta

## Purpose

Scopes the brand-naming text to reality: the footer is home-feed-only
(C8-02) and the titles scenario covers the web UI (C8-03). No scenario or
test changes.

## MODIFIED Requirements

### Requirement: Brand naming
The product name displayed to users SHALL be "Instagram": every page title
of the web UI ends with "· Instagram" (page titles default to "Instagram";
the API documentation and admin console are separate surfaces with their
own titles), the sidebar of every authenticated page shows the brand name,
the sidebar footer reads "© 2026 Instagram" and appears only on the home
feed, the auth logo wordmark reads "Instagram" and the OpenAPI title is
"Instagram API".

#### Scenario: Page titles carry the brand
- **WHEN** a visitor opens any page of the web UI
- **THEN** the document title ends with "· Instagram" (or is exactly "Instagram" when no page-specific title is set)

#### Scenario: Auth wordmark shows the brand
- **WHEN** a visitor opens the login or register page
- **THEN** the auth logo wordmark reads "Instagram"

#### Scenario: Sidebar and footer show the brand
- **WHEN** a logged-in user views an authenticated page
- **THEN** the sidebar shows the brand name "Instagram", and on the home feed — and only there — the sidebar footer reads "© 2026 Instagram"
