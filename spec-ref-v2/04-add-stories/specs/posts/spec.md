# Spec Delta

## Purpose

Fulfils the last declared dependency of the posts listing requirement: the
stories bar renders above the feed and the home render purges expired
stories.

## MODIFIED Requirements

### Requirement: Post listing
The system SHALL list a user's own posts ordered by creation date, newest
first, with limit/offset pagination through `GET /api/posts/` and the
owner's profile grid. The home page SHALL show posts from the users the
logged-in user follows (defined in the social capability) instead of their
own posts, with the stories bar (defined in the stories capability) rendered
above the post list, and SHALL load further pages through HTMX infinite
scroll. A non-HTMX request with a page parameter SHALL render the full page
with the posts of that window. Rendering the home page SHALL purge expired
stories before display. Post cards SHALL show the post's first media file
together with the caption, owner and timestamp. The API list responses SHALL
include a `first_image_url` field with the post's first image media (used for
card thumbnails), or an empty value when the post has no image media.

#### Scenario: Feed shows followed users' posts
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows posts from the users they follow as post cards (first media file, caption, owner, timestamp), newest first, below the stories bar

#### Scenario: API list of own posts
- **WHEN** a client requests `GET /api/posts/` with optional limit and offset
- **THEN** the system responds 200 with the authenticated user's own posts, newest first

#### Scenario: API list includes first image thumbnail
- **WHEN** a post in the API list response has image media
- **THEN** the response includes `first_image_url` pointing to the post's first image media file, and the field is empty for a post without image media

#### Scenario: Pagination window
- **WHEN** a listing has more posts than the page size
- **THEN** the system returns only the requested window (limit/offset) without duplicates across pages

#### Scenario: Feed loads more posts on scroll
- **WHEN** the browser reaches the feed sentinel and requests the next page with the HTMX header
- **THEN** the system responds with only the next window of post cards plus the next sentinel (or the end marker), without the page shell

#### Scenario: Non-HTMX request with a page parameter renders the full page
- **WHEN** a browser requests the home page with a page parameter and no HTMX header
- **THEN** the system renders the full page showing the posts of that page window
