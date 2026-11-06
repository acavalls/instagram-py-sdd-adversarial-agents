# Spec Delta

## MODIFIED Requirements

### Requirement: Authenticated landing placeholder
The system SHALL serve a personal posts feed page at `/web/feed/` that
requires an authenticated session and acts as the landing page after web
login. The page SHALL show the logged-in user's own posts as provided by the
`posts` capability. The followed-users feed is owned by a later change.

#### Scenario: Placeholder requires login
- **WHEN** an anonymous visitor requests `/web/feed/`
- **THEN** the system redirects to the login page

#### Scenario: Logged-in user reaches the placeholder
- **WHEN** a logged-in user requests `/web/feed/`
- **THEN** the system renders the personal posts feed page showing their own posts
