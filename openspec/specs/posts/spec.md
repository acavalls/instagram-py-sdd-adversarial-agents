# posts Specification

## Purpose
Lets a user publish posts with media and manage them: create (with generated
placeholder media from the web UI), list their own posts, view a single post,
update the caption and delete. It owns post data and ownership rules;
everything social (follows, feed of followed users, stories) builds on it.

## Requirements

### Requirement: Post data model
The system SHALL store a post with a UUID identifier, an owner, an optional
caption of at most 2200 characters, and creation/update timestamps. The
system SHALL store post media as up to 10 ordered files attached to a post,
each with a media type (image or video) and a zero-based order. Posts SHALL
be listed newest first with a deterministic order (creation date descending,
then identifier descending) so pagination windows are stable. The caption
limit MUST hold on every storage path, including queryset bulk operations:
an over-limit literal caption is refused with nothing stored, and a
non-literal caption value (an expression with no text to validate) is
refused with the model's caption validation error on the batched paths. The
media limit MUST hold on every storage path too: a bulk write that would
exceed a post's media capacity stores only what fits (and nothing for the
rejected rows), never exceeding the cap. Legal bulk updates of captions and
media MUST apply.

#### Scenario: Post persisted with media
- **GIVEN** a user creates a post with a caption and media files
- **THEN** the system stores the post with UUID identifier and its media ordered by position, newest posts first in listings

#### Scenario: Caption length limit
- **WHEN** a post is created or updated with a caption longer than 2200 characters
- **THEN** the system rejects it with a field-level validation error

#### Scenario: Bulk paths refuse over-limit captions
- **WHEN** a queryset bulk write (update, bulk create or bulk update) would store a literal caption longer than 2200 characters
- **THEN** the system stores nothing for that caption and returns or keeps only the compliant rows, without raising

#### Scenario: Non-literal caption write refused
- **WHEN** a bulk create or bulk update carries a non-literal caption value (an expression instead of a string)
- **THEN** the system refuses the whole write with the model's caption validation error

#### Scenario: Non-literal caption update refuses silently
- **WHEN** a queryset `update()` carries a non-literal caption value (an expression instead of a string)
- **THEN** the system writes nothing and reports zero updated rows without raising

#### Scenario: Legal caption bulk update applies
- **WHEN** a bulk update carries a literal caption within the limit for every object
- **THEN** the system writes the new captions and reports the updated rows

#### Scenario: Bulk paths keep the media limit
- **WHEN** a queryset bulk write on post media would leave a target post with more than 10 media files
- **THEN** the system stores only the rows that fit (and nothing for the rows that would exceed the cap), never exceeding the limit on any post

### Requirement: Post creation
The system SHALL allow a logged-in user to create a post with an optional
caption and up to 10 media files. From the web UI, the system SHALL create
the post with a generated placeholder image when no file is provided. The
system MUST NOT require media for a post to be valid. The API SHALL trim
surrounding whitespace from captions; a caption that is empty after
trimming is stored as the empty string.

#### Scenario: Successful web creation
- **WHEN** a logged-in user requests post creation from the web UI
- **THEN** the system creates a post with a random caption from the app's caption list and a generated placeholder image, and confirms with the toast "Post created!"

#### Scenario: Successful API creation
- **WHEN** a client posts a caption and up to 10 images to `POST /api/posts/`
- **THEN** the system responds 201 with the created post (id, owner_username, caption, media with order and media_type, media_count)

#### Scenario: API creation with too many media files
- **WHEN** a client posts more than 10 media files to `POST /api/posts/`
- **THEN** the system responds 400 with a validation error

#### Scenario: Whitespace-only caption becomes empty
- **WHEN** a client posts a caption consisting only of whitespace to `POST /api/posts/`
- **THEN** the system stores the caption as the empty string

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

### Requirement: Post detail
The system SHALL allow retrieving a single post by identifier. An unknown
identifier MUST respond 404.

#### Scenario: Existing post detail
- **WHEN** a client requests `GET /api/posts/<uuid>/` for an existing post
- **THEN** the system responds 200 with the post data including its media

#### Scenario: Unknown post detail
- **WHEN** a client requests `GET /api/posts/<uuid>/` for a post that does not exist
- **THEN** the system responds 404 with the error "Post not found"

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

### Requirement: Post deletion
The system SHALL allow the owner of a post to delete it, removing its media
with it. A non-owner MUST receive 403 with the error "You can only delete
your own posts". From the web UI, deletion SHALL remove the post card and
confirm with the toast "Post deleted!".

#### Scenario: Owner deletes post via API
- **WHEN** the owner sends `DELETE /api/posts/<uuid>/`
- **THEN** the system responds 204 and the post and its media no longer exist

#### Scenario: Non-owner deletion rejected
- **WHEN** a user sends `DELETE /api/posts/<uuid>/` for a post they do not own
- **THEN** the system responds 403 with the error "You can only delete your own posts"

#### Scenario: Web deletion removes the card
- **WHEN** the owner deletes a post from their post cards
- **THEN** the system removes the post card and shows the toast "Post deleted!"

### Requirement: Post visibility
The system SHALL make posts visible through the owner's post listings and
the owner's API listings. `GET /api/posts/` and the other API endpoints of
this capability MUST only return or mutate the authenticated user's own
posts.

#### Scenario: No cross-user listing
- **WHEN** a user lists their posts via the posts API while other users have posts
- **THEN** the system returns only the authenticated user's own posts

### Requirement: Post media storage
The system SHALL store post media files under the media root in a
`post_media/` path. Stored files MUST be reachable through their media URL
in API responses and web templates.

#### Scenario: Media stored under the post media path
- **WHEN** a post with media files is created
- **THEN** each file is stored under `post_media/` inside the media root and its media URL resolves
