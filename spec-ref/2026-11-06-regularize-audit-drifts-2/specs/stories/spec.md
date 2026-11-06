# Spec Delta

## MODIFIED Requirements

### Requirement: Story creation
The system SHALL allow a logged-in user to create a story via
`POST /web/stories/create/` without uploading a file; the system generates the
media automatically as a placeholder image. On success the response SHALL
render a success toast ("Story created") and an out-of-band re-render of the
stories bar. An unauthenticated request MUST be rejected.

#### Scenario: Successful web creation
- **WHEN** a logged-in user submits `POST /web/stories/create/`
- **THEN** the system creates a story with a generated placeholder image and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Unauthenticated creation rejected
- **WHEN** an anonymous client submits `POST /web/stories/create/`
- **THEN** the system rejects the request instead of creating a story

### Requirement: Story view tracking
The system SHALL record a view when a logged-in user opens a followed user's
active story via `POST /web/stories/<uuid:story_id>/view/`; the response SHALL
render a success toast ("Story viewed") and an out-of-band updated stories
bar. A (story, viewer) pair SHALL be recorded at most once; marking the same
story again MUST NOT duplicate the record. A user MUST NOT record a view of
their own story, an expired story, or a story owned by a user the viewer does
not follow. An unknown story identifier MUST NOT record any view and MUST be
reported as not found.

#### Scenario: First view recorded
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a followed user's active story they have not seen
- **THEN** the system records the view once and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Repeated view is idempotent
- **WHEN** the same user marks the same story as viewed again
- **THEN** no duplicate view record is created

#### Scenario: Self-view rejected
- **WHEN** a user submits `POST /web/stories/<uuid>/view/` for their own story
- **THEN** the system does not record a view and reports the error

#### Scenario: Non-followed story not viewable
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a story owned by a user they do not follow
- **THEN** the system does not record the view

#### Scenario: Expired story not viewable
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a story whose expiration timestamp has passed
- **THEN** the system does not record the view and reports that the story has expired

#### Scenario: Unknown story reported as not found
- **WHEN** a logged-in user submits `POST /web/stories/<uuid>/view/` for a story identifier that does not exist
- **THEN** the system does not record any view and reports that the story was not found
