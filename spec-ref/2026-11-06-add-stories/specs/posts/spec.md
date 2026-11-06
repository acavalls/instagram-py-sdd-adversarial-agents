# Spec Delta

## MODIFIED Requirements

### Requirement: Post listing
The system SHALL list a user's own posts ordered by creation date, newest
first, with limit/offset pagination through `GET /api/posts/` and the
owner's profile grid. The home page SHALL show posts from the users the
logged-in user follows (defined in the social capability) instead of their
own posts, with the stories bar (defined in the stories capability) rendered
above the post list. Rendering the home page SHALL purge expired stories
before display.

#### Scenario: Personal feed on the home page
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows posts from the users they follow as post cards (media, caption, owner, timestamp), newest first, below the stories bar

#### Scenario: API list of own posts
- **WHEN** a client requests `GET /api/posts/` with optional limit and offset
- **THEN** the system responds 200 with the authenticated user's own posts, newest first

#### Scenario: Pagination window
- **WHEN** a listing has more posts than the page size
- **THEN** the system returns only the requested window (limit/offset) without duplicates across pages
