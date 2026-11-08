# Spec Delta

## Purpose

Replaces the declared personal-feed stepping stone: the home page now shows
the followed-users feed, and the caption limit is proven on the web edit
path.

## MODIFIED Requirements

### Requirement: Post listing
The system SHALL list a user's own posts ordered by creation date, newest
first, with limit/offset pagination through `GET /api/posts/` and the
owner's profile grid. The home page SHALL show posts from the users the
logged-in user follows (defined in the social capability) instead of their
own posts, and SHALL load further pages through HTMX infinite scroll. A
non-HTMX request with a page parameter SHALL render the full page with the
posts of that window. Post cards SHALL show the post's first media file
together with the caption, owner and timestamp. The API list responses SHALL
include a `first_image_url` field with the post's first image media (used for
card thumbnails), or an empty value when the post has no image media.

#### Scenario: Personal feed on the feed page
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows posts from the users they follow as post cards (first media file, caption, owner, timestamp), newest first

#### Scenario: API list of own posts
- **WHEN** a client requests `GET /api/posts/` with optional limit and offset
- **THEN** the system responds 200 with the authenticated user's own posts, newest first

#### Scenario: API list includes first image thumbnail
- **WHEN** a post in the API list response has image media
- **THEN** the response includes `first_image_url` pointing to the post's first image media file, and the field is empty for a post without image media

#### Scenario: Pagination window
- **WHEN** a listing has more posts than the page size
- **THEN** the system returns only the requested window (limit/offset) without duplicates across pages

#### Scenario: Home feed loads more posts on scroll
- **WHEN** the browser reaches the feed sentinel and requests the next page with the HTMX header
- **THEN** the system responds with only the next window of post cards plus the next sentinel (or the end marker), without the page shell

#### Scenario: Non-HTMX request with a page parameter renders the full page
- **WHEN** a browser requests the home page with a page parameter and no HTMX header
- **THEN** the system renders the full page showing the posts of that page window

