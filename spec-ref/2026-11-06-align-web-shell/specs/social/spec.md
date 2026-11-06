# Spec Delta

## MODIFIED Requirements

### Requirement: User profile page
The system SHALL show a profile page for every user at
`/web/profile/<uuid>/` with their posts newest first (paginated) and
counters of posts, followers and following. An unknown identifier MUST
respond 404. On their own profile the owner sees the edit and delete
controls on their posts; on other profiles the visitor sees the follow
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

### Requirement: Following list
A profile SHALL offer a modal listing the users that profile follows,
searchable by username or name.

#### Scenario: Following list shows followed users
- **WHEN** a visitor opens the following list of a profile
- **THEN** the system shows the users that profile follows

#### Scenario: Following list search filters
- **WHEN** a visitor types a query in the following list search
- **THEN** the system shows only the followed users whose username or name matches the query
