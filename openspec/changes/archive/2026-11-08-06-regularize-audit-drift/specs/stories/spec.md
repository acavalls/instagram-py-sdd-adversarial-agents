# Spec Delta

## Purpose

Declares the stories contracts that tests already pin: the non-HTMX redirect
fallback, the malformed-identifier 404 and the ORM bulk-path expiry scope.

## MODIFIED Requirements

### Requirement: Story data model
The system SHALL persist stories owned by a user, each with image media stored
under a dated path (`stories/<year>/<month>/<day>/`), a creation timestamp, and
an expiration timestamp set to exactly 24 hours after creation. The 24-hour
lifetime MUST hold on the save path: a story saved without an expiration
timestamp gets `created_at + 24h`, and an explicitly provided expiration
timestamp that differs from `created_at + 24h` MUST be rejected with a
validation error. The invariant is scoped to the save path: queryset
`update()` and `bulk_create` writes bypass it and store the expiry values
they are given. A story whose expiration timestamp has passed SHALL be
considered expired and MUST NOT appear as active anywhere in the system.

#### Scenario: Story persisted with placeholder media
- **WHEN** a story is created for a user
- **THEN** the story is stored with an image file under the dated stories path, a creation timestamp, and an expiration timestamp exactly 24 hours later

#### Scenario: Mismatching explicit expiry rejected
- **WHEN** a story is saved with an explicit expiration timestamp that differs from its creation timestamp plus exactly 24 hours
- **THEN** the system refuses to save the story with a validation error

#### Scenario: Expired story is not active
- **WHEN** a story's expiration timestamp has passed
- **THEN** the story is not returned as an active story for its owner, for any feed, and is removed from the stories bar

#### Scenario: Bulk paths bypass the save-path expiry invariant
- **WHEN** stories are written through queryset `update()` or `bulk_create` carrying an arbitrary expiration timestamp
- **THEN** the write succeeds and stores the given value, because the 24-hour invariant is scoped to the save path

### Requirement: Story creation
The system SHALL allow a logged-in user to create a story via
`POST /web/stories/create/` without uploading a file; the system generates the
media automatically as a placeholder image. On success the response SHALL
render a success toast ("Story created") and an out-of-band re-render of the
stories bar. A non-HTMX client SHALL instead be redirected to the feed after
the action. An unauthenticated request MUST be rejected.

#### Scenario: Successful web creation
- **WHEN** a logged-in user submits `POST /web/stories/create/`
- **THEN** the system creates a story with a generated placeholder image and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Unauthenticated creation rejected
- **WHEN** an anonymous client submits `POST /web/stories/create/`
- **THEN** the system rejects the request instead of creating a story

#### Scenario: Non-HTMX creation redirects to the feed
- **WHEN** a logged-in non-HTMX client submits `POST /web/stories/create/`
- **THEN** the system creates the story and responds with a redirect to the feed instead of the HTMX toast fragment

### Requirement: Story view tracking
The system SHALL record a view when a logged-in user opens a followed user's
active story via `POST /web/stories/<uuid:story_id>/view/`; the response SHALL
render a success toast ("Story viewed") and an out-of-band updated stories
bar. A (story, viewer) pair SHALL be recorded at most once; marking the same
story again MUST NOT duplicate the record. A user MUST NOT record a view of
their own story. Stories of users the viewer does not follow MUST NOT be
viewable. Every rejected view attempt SHALL respond with HTTP 200, render an
error toast and re-render the stories bar out of band, without recording a
view, using these texts: "Story not found" for an unknown or expired story
identifier, "You cannot view your own story" for self-views, and "You can
only view stories from people you follow" for non-followed owners' stories.
A malformed (non-UUID) story identifier SHALL be rejected at the routing
layer with 404. A non-HTMX client SHALL instead be redirected to the feed
after the action.

#### Scenario: First view recorded
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a followed user's active story they have not seen
- **THEN** the system records the view once and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Repeated view is idempotent
- **WHEN** the same user marks the same story as viewed again
- **THEN** no duplicate view record is created

#### Scenario: Self-view rejected
- **WHEN** a user submits `POST /web/stories/<uuid>/view/` for their own story
- **THEN** the system does not record a view and renders the error toast "You cannot view your own story" with an out-of-band updated stories bar

#### Scenario: Non-followed story not viewable
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a story owned by a user they do not follow
- **THEN** the system does not record the view and renders the error toast "You can only view stories from people you follow" with an out-of-band updated stories bar

#### Scenario: Unknown or expired story rejected
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for an unknown or expired story identifier
- **THEN** the system does not record a view and renders the error toast "Story not found" with an out-of-band updated stories bar

#### Scenario: Malformed story identifier responds 404
- **WHEN** a logged-in user submits `POST /web/stories/<malformed>/view/` with a value that is not a UUID
- **THEN** the system responds 404 at the routing layer, records no view and renders no toast fragment

#### Scenario: Non-HTMX view redirects to the feed
- **WHEN** a logged-in non-HTMX client submits `POST /web/stories/<uuid>/view/`
- **THEN** the system performs the action (or records the rejection) and responds with a redirect to the feed instead of the HTMX toast fragment
