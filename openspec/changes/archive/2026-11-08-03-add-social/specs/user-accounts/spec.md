# Spec Delta

## Purpose

Fulfils the authenticated landing placeholder with the real social feed:
the landing page now shows the followed-users feed and the placeholder
state disappears.

## MODIFIED Requirements

### Requirement: Authenticated landing placeholder
The system SHALL serve a feed page at `/web/feed/` that requires an
authenticated session and acts as the landing page after web login. The page
SHALL show the posts of the users the logged-in user follows, as defined in
the `social` capability. The user's own posts remain reachable through the
posts API.

#### Scenario: Placeholder requires login
- **WHEN** an anonymous visitor requests `/web/feed/`
- **THEN** the system redirects to the login page

#### Scenario: Logged-in user reaches the placeholder
- **WHEN** a logged-in user requests `/web/feed/`
- **THEN** the system renders the feed page showing posts from the users they follow
