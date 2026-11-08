# Spec Delta

## Purpose

Declares the pagination-parameters rejection and the web inline-edit routing
contract that tests already pin.

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
stories before display. A listing request whose pagination parameters are
not positive integers (a non-integer, zero or negative limit, or a negative
offset) MUST be rejected with 400 and the error "Invalid pagination
parameters". Post cards SHALL show the post's first media file together with
the caption, owner and timestamp, and the card header's username link SHALL
point to the owner's profile page. The API list responses SHALL include a
`first_image_url` field with the post's first image media (used for card
thumbnails), or an empty value when the post has no image media.

#### Scenario: Personal feed on the feed page
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

#### Scenario: Home feed loads more posts on scroll
- **WHEN** the browser reaches the feed sentinel and requests the next page with the HTMX header
- **THEN** the system responds with only the next window of post cards plus the next sentinel (or the end marker), without the page shell

#### Scenario: Non-HTMX request with a page parameter renders the full page
- **WHEN** a browser requests the home page with a page parameter and no HTMX header
- **THEN** the system renders the full page showing the posts of that page window

#### Scenario: Invalid pagination parameters rejected
- **WHEN** a client requests `GET /api/posts/` with a non-integer, zero or negative limit, or a negative offset
- **THEN** the system responds 400 with the error "Invalid pagination parameters"

### Requirement: Caption update
The system SHALL allow the owner of a post to update its caption. A
non-owner MUST receive 403 with the error "You can only edit your own
posts". From the web UI, the caption edit SHALL be an inline form that
updates the post without leaving the card and confirms with the toast "Post
updated!". The web edit form's GET MUST refuse unknown posts and posts the
requester does not own with 404, without revealing the caption; a non-owner
POST to the web edit endpoint MUST be refused with 403 and the ownership
error.

#### Scenario: Owner updates caption via API
- **WHEN** the owner sends `PATCH /api/posts/<uuid>/` with a new caption
- **THEN** the system responds 200 with the updated post

#### Scenario: Non-owner update rejected
- **WHEN** a user sends `PATCH /api/posts/<uuid>/` for a post they do not own
- **THEN** the system responds 403 with the error "You can only edit your own posts"

#### Scenario: Inline web edit
- **WHEN** the owner submits the inline edit form on one of their post cards
- **THEN** the system updates the caption, closes the form and shows the toast "Post updated!"

#### Scenario: Cancel inline edit
- **WHEN** the owner cancels the inline edit form (or submits an unknown post id)
- **THEN** the system closes the form without changing the post

#### Scenario: Web edit form refuses unknown or non-owner posts
- **WHEN** a user requests the web edit form of an unknown post or a post they do not own
- **THEN** the system responds 404 without revealing the post's caption

#### Scenario: Web edit POST refuses a non-owner
- **WHEN** a user submits the web edit form of a post they do not own
- **THEN** the system responds 403 with the error "You can only edit your own posts" and the post is unchanged
