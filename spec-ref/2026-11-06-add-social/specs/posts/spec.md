# Spec Delta — posts (MODIFIED / ADDED)

## MODIFIED Requirements

### Requirement: Post listing
The system SHALL list a user's own posts ordered by creation date, newest
first, with limit/offset pagination through `GET /api/posts/` and the
owner's profile grid. The home page SHALL show posts from the users the
logged-in user follows (defined in the social capability) instead of their
own posts.

#### Scenario: Personal feed on the home page
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows posts from the users they follow as post cards (media, caption, owner, timestamp), newest first

#### Scenario: API list of own posts
- **WHEN** a client requests `GET /api/posts/` with optional limit and offset
- **THEN** the system responds 200 with the authenticated user's own posts, newest first

#### Scenario: Pagination window
- **WHEN** a listing has more posts than the page size
- **THEN** the system returns only the requested window (limit/offset) without duplicates across pages

### Requirement: Post visibility
The system SHALL make posts visible through the owner's profile grid, the
followed-users home feed and the owner's API listings. `GET /api/posts/` and
the other API endpoints of this capability MUST only return or mutate the
authenticated user's own posts.

#### Scenario: No cross-user listing
- **WHEN** a user lists their posts via the posts API while other users have posts
- **THEN** the system returns only the authenticated user's own posts

## ADDED Requirements

### Requirement: Post media storage
The system SHALL store post media files under the media root in a
`post_examples/<year>/<month>/<day>/` path derived from the upload date.
Stored files MUST be reachable through their media URL in API responses and
web templates.

#### Scenario: Media stored under dated path
- **WHEN** a post with media files is created
- **THEN** each file is stored under `post_examples/<year>/<month>/<day>/` and its media URL resolves
