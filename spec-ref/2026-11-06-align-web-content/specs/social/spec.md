# Spec Delta

## MODIFIED Requirements

### Requirement: Followed-users feed
The system SHALL show a logged-in user a home feed of posts from the users
they follow, ordered newest first and loaded through HTMX infinite scroll.
When the user follows nobody, the feed SHALL show an empty state inviting
them to share their first photo.

#### Scenario: Feed shows followed users' posts
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows post cards of the users they follow, newest first

#### Scenario: Feed ordered newest first with pagination
- **WHEN** the feed has more posts than the page size
- **THEN** the system loads the remaining posts page by page through the infinite scroll sentinel

#### Scenario: Empty feed state
- **WHEN** a logged-in user with no follows and no followed posts visits the home page
- **THEN** the system shows an empty feed state with an icon, the title "Share Photos", a subtitle and a call to action

### Requirement: User suggestions
The home feed sidebar SHALL suggest up to five users to follow, excluding
the logged-in user and everyone they already follow, preferring the newest
accounts. Each suggestion SHALL show the avatar, the username and a follow
button.

#### Scenario: Suggestions exclude followed users and self
- **WHEN** the sidebar renders suggestions
- **THEN** the logged-in user and their follows do not appear among the suggestions

#### Scenario: Suggestions limited to newest accounts
- **WHEN** more candidates than the limit exist
- **THEN** the system shows only the five newest accounts

#### Scenario: Suggestion rows show avatar and follow button
- **WHEN** the sidebar renders a suggestion
- **THEN** the row shows the suggested user's avatar, their username and a follow button

### Requirement: User profile page
The system SHALL show a profile page for every user at
`/web/profile/<uuid>/` with their posts newest first, loaded through HTMX
infinite scroll, and counters of posts, followers and following. An unknown
identifier MUST respond 404. On their own profile the owner sees the edit and
delete controls on their posts; on other profiles the visitor sees the follow
button reflecting the current relationship. The sidebar (defined in the
web-ui capability) SHALL link to the logged-in user's own profile page.

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
