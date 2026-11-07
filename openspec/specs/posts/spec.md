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
then identifier descending) so pagination windows are stable.

#### Scenario: Post persisted with media
- **GIVEN** a user creates a post with a caption and media files
- **THEN** the system stores the post with UUID identifier and its media ordered by position, newest posts first in listings

#### Scenario: Caption length limit
- **WHEN** a post is created or updated with a caption longer than 2200 characters
- **THEN** the system rejects it with a field-level validation error

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
above the post list. Rendering the home page SHALL purge expired stories
before display. Post cards SHALL show the post's first media file together
with the caption, owner and timestamp.

#### Scenario: Personal feed on the feed page
- **WHEN** a logged-in user visits the home page
- **THEN** the system shows posts from the users they follow as post cards (first media file, caption, owner, timestamp), newest first, below the stories bar

#### Scenario: API list of own posts
- **WHEN** a client requests `GET /api/posts/` with optional limit and offset
- **THEN** the system responds 200 with the authenticated user's own posts, newest first

#### Scenario: Pagination window
- **WHEN** a listing has more posts than the page size
- **THEN** the system returns only the requested window (limit/offset) without duplicates across pages

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
updates the post without leaving the profile grid and confirms with the
toast "Post updated!".

#### Scenario: Owner updates caption via API
- **WHEN** the owner sends `PATCH /api/posts/<uuid>/` with a new caption
- **THEN** the system responds 200 with the updated post

#### Scenario: Non-owner update rejected
- **WHEN** a user sends `PATCH /api/posts/<uuid>/` for a post they do not own
- **THEN** the system responds 403 with the error "You can only edit your own posts"

#### Scenario: Inline web edit
- **WHEN** the owner submits the inline edit form on the profile grid
- **THEN** the system updates the caption, closes the form and shows the toast "Post updated!"

#### Scenario: Cancel inline edit
- **WHEN** the owner cancels the inline edit form (or submits an unknown post id)
- **THEN** the system closes the form without changing the post

### Requirement: Post deletion
The system SHALL allow the owner of a post to delete it, removing its media
with it. A non-owner MUST receive 403 with the error "You can only delete
your own posts". From the web UI, deletion SHALL remove the post from the
profile grid and confirm with the toast "Post deleted!".

#### Scenario: Owner deletes post via API
- **WHEN** the owner sends `DELETE /api/posts/<uuid>/`
- **THEN** the system responds 204 and the post and its media no longer exist

#### Scenario: Non-owner deletion rejected
- **WHEN** a user sends `DELETE /api/posts/<uuid>/` for a post they do not own
- **THEN** the system responds 403 with the error "You can only delete your own posts"

#### Scenario: Web deletion removes the card
- **WHEN** the owner deletes a post from the profile grid
- **THEN** the system removes the post card from the grid and shows the toast "Post deleted!"

### Requirement: Post visibility
The system SHALL make posts visible through the owner's profile grid, the
followed-users home feed and the owner's API listings. `GET /api/posts/` and
the other API endpoints of this capability MUST only return or mutate the
authenticated user's own posts.

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
