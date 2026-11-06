# Spec Delta — social (MODIFIED)

## MODIFIED Requirements

### Requirement: User profile page
The system SHALL show a profile page for every user at
`/web/profile/<uuid>/` with their posts newest first (paginated) and
counters of posts, followers and following. An unknown identifier MUST
respond 404. On their own profile the owner sees the edit and delete
controls on their posts; on other profiles the visitor sees the follow
button reflecting the current relationship. The topbar SHALL link to the
logged-in user's own profile page.

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
- **WHEN** a logged-in user views any page with the topbar
- **THEN** the topbar shows a Profile link pointing to their own profile page
