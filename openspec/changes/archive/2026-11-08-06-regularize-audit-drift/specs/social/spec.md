# Spec Delta

## Purpose

Declares the profile page's non-HTMX full-page window that the posts
capability already declares for the home page.

## MODIFIED Requirements

### Requirement: User profile page
The system SHALL show a profile page for every user at
`/web/profile/<uuid>/` with their posts newest first, loaded through HTMX
infinite scroll, and counters of posts, followers and following. A non-HTMX
request with a page parameter SHALL render the full page with the posts of
that window. An unknown identifier MUST respond 404. On their own profile
the owner sees the edit and delete controls on their posts; on other profiles
the visitor sees the follow button reflecting the current relationship. The
sidebar (defined in the web-ui capability) SHALL link to the logged-in
user's own profile page. A profile without posts SHALL show an empty grid
message instead of grid items.

#### Scenario: Own profile shows stats and editable grid
- **WHEN** a user visits their own profile page
- **THEN** the system shows their posts, followers and following counters, with edit and delete controls on their own posts

#### Scenario: Other user profile shows stats and follow state
- **WHEN** a user visits another user's profile page
- **THEN** the system shows the profile's posts and counters and a follow button reflecting whether the visitor already follows them

#### Scenario: Unknown profile responds 404
- **WHEN** a client requests the profile page of a non-existent user
- **THEN** the system responds 404

#### Scenario: Topbar links to own profile
- **WHEN** a logged-in user views any authenticated web page
- **THEN** the sidebar shows a Profile link pointing to their own profile page

#### Scenario: Profile grid loads more posts on scroll
- **WHEN** the browser reaches the profile grid sentinel and requests the next page with the HTMX header
- **THEN** the system responds with only the next window of grid items plus the next sentinel (or the end marker), without the page shell

#### Scenario: Profile grid without posts shows an empty message
- **WHEN** a user visits the profile page of a user with no posts
- **THEN** the system shows the empty grid message "No posts yet." instead of grid items

#### Scenario: Non-HTMX profile request with a page parameter renders the full page
- **WHEN** a browser requests a profile page with a page parameter and no HTMX header
- **THEN** the system renders the full page showing the posts of that page window
