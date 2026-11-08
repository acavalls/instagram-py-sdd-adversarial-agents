# Spec Delta

## Purpose

Declares the brand visual style of the auth screens (Google Fonts + brand
gradient) and keeps every previously declared element intact.

## MODIFIED Requirements

### Requirement: Auth layout
The login and register pages SHALL render in a dedicated auth layout: an
`auth-page` body with a centered auth card showing the app logo and the
form, a secondary card linking to the counterpart page, and footer links.
The auth layout MUST NOT include the authenticated app sidebar. The auth
screens SHALL implement the brand visual style: the brand Google Fonts
(a script display font for the logo, a body font for the form) and the
brand gradient painting the page background behind the light cards.

#### Scenario: Login renders the auth card
- **WHEN** a visitor opens the login page
- **THEN** the page renders an auth card with the logo and the login form, plus a secondary card linking to the register page

#### Scenario: Register renders the auth card
- **WHEN** a visitor opens the register page
- **THEN** the page renders an auth card with the logo and the register form, plus a secondary card linking to the login page

#### Scenario: Auth screens use the brand visual style
- **WHEN** a visitor opens the login or register page
- **THEN** the page loads the brand fonts (a script display font and a body font) and the auth background carries the brand gradient

## ADDED Requirements

### Requirement: Brand naming
The product name displayed to users SHALL be "Instagram": every page title
ends with "· Instagram" (page titles default to "Instagram"), the sidebar
of every authenticated page shows the brand name, the home feed's sidebar
footer reads "© 2026 Instagram", the auth logo wordmark reads "Instagram"
and the OpenAPI title is "Instagram API".

#### Scenario: Page titles carry the brand
- **WHEN** a visitor opens any page of the application
- **THEN** the document title ends with "· Instagram" (or is exactly "Instagram" when no page-specific title is set)

#### Scenario: Auth wordmark shows the brand
- **WHEN** a visitor opens the login or register page
- **THEN** the auth logo wordmark reads "Instagram"

#### Scenario: Sidebar and footer show the brand
- **WHEN** a logged-in user views an authenticated page
- **THEN** the sidebar shows the brand name "Instagram", and on the home feed the sidebar footer reads "© 2026 Instagram"
