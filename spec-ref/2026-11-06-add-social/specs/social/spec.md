# Spec Delta — social (new capability)

## Purpose

Lets users connect with each other: follow and unfollow, see a feed built
from the users they follow, discover accounts through suggestions, visit
profile pages with public stats, and browse who someone follows. It owns
the follow relationship and feed aggregation; stories build on it later.

## ADDED Requirements

### Requirement: Follow relationship data
The system SHALL store a follow relationship with a UUID identifier, a
follower, a followed user and a creation timestamp. A (follower, following)
pair MUST be unique and a user MUST NOT follow themselves.

#### Scenario: Follow persisted
- **WHEN** a user follows another user
- **THEN** the system stores the relationship with a UUID identifier and a creation timestamp

#### Scenario: Self-follow rejected
- **WHEN** a user attempts to follow themselves
- **THEN** the system rejects it with the error "You cannot follow yourself"

#### Scenario: Duplicate follow rejected
- **WHEN** a user attempts to follow a user they already follow
- **THEN** the system rejects it with the error "Already following this user"

### Requirement: Follow and unfollow actions
The system SHALL allow a logged-in user to follow and unfollow any other
user through the web UI via an HTMX button that toggles in place and
confirms with a toast.

#### Scenario: Web follow via HTMX
- **WHEN** a logged-in user clicks the follow button on a profile
- **THEN** the button toggles to the following state and the toast "Followed successfully" is shown

#### Scenario: Web unfollow via HTMX
- **WHEN** a logged-in user clicks the following button
- **THEN** the button toggles back to the follow state and the toast "Unfollowed successfully" is shown

#### Scenario: Web follow failure shows the cause
- **WHEN** a follow or unfollow action fails (self-follow, duplicate, or unknown relationship)
- **THEN** the button keeps its current state and an error toast shows the failure reason

### Requirement: Followed-users feed
The home page SHALL show posts from the users the logged-in user follows,
ordered by creation date newest first, paginated. When the user follows
nobody, the home page SHALL show an empty state pointing to suggestions.

#### Scenario: Feed shows followed users' posts
- **WHEN** a logged-in user visits the home page and follows users with posts
- **THEN** the system shows only those followed users' posts as post cards

#### Scenario: Feed ordered newest first with pagination
- **WHEN** the followed users have more posts than the page size
- **THEN** the system shows the newest first and offers pagination without duplicates across pages

#### Scenario: Empty feed state
- **WHEN** a logged-in user with no follows visits the home page
- **THEN** the system shows an empty state instead of post cards

### Requirement: User suggestions
The home page SHALL suggest up to 5 users the logged-in user does not
follow, excluding themselves, newest accounts first.

#### Scenario: Suggestions exclude followed users and self
- **WHEN** the suggestions panel is rendered for a user
- **THEN** it never contains the user themselves nor anyone they already follow

#### Scenario: Suggestions limited to newest accounts
- **WHEN** more than 5 unfollowed users exist
- **THEN** the system shows only the 5 most recently joined accounts

### Requirement: User profile page
The system SHALL show a profile page for every user at
`/web/profile/<uuid>/` with their posts newest first (paginated) and
counters of posts, followers and following. An unknown identifier MUST
respond 404. On their own profile the owner sees the edit and delete
controls on their posts; on other profiles the visitor sees the follow
button reflecting the current relationship.

#### Scenario: Own profile shows stats and editable grid
- **WHEN** a user visits their own profile page
- **THEN** the system shows their posts, followers and following counters, with edit and delete controls on their own posts

#### Scenario: Other user profile shows stats and follow state
- **WHEN** a user visits another user's profile page
- **THEN** the system shows the profile's posts and counters and a follow button reflecting whether the visitor already follows them

#### Scenario: Unknown profile responds 404
- **WHEN** a client requests the profile page of a non-existent user
- **THEN** the system responds 404

### Requirement: Following list
A profile SHALL offer a modal listing the users that profile follows,
searchable by username or name.

#### Scenario: Following list shows followed users
- **WHEN** a visitor opens the following list of a profile
- **THEN** the system shows the users that profile follows

#### Scenario: Following list search filters
- **WHEN** a visitor types a query in the following list search
- **THEN** the system shows only the followed users whose username or name matches the query
