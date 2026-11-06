# Spec Delta

## Purpose

Ephemeral 24-hour stories: a user publishes a temporary image that expires
after one day, followers see those stories on the home page stories bar, and
views are tracked per viewer. Mirrors the story feature of the reference app
(`/home/ale/mapfre/personal/django_ig`, `apps/posts` Story/StoryView models and
`StoryService`).

## ADDED Requirements

### Requirement: Story data model
The system SHALL persist stories owned by a user, each with image media stored
under a dated path (`stories/<year>/<month>/<day>/`), a creation timestamp, and
an expiration timestamp set to 24 hours after creation. A story whose
expiration timestamp has passed SHALL be considered expired and MUST NOT appear
as active anywhere in the system.

#### Scenario: Story persisted with placeholder media
- **WHEN** a story is created for a user
- **THEN** the story is stored with an image file under the dated stories path, a creation timestamp, and an expiration timestamp exactly 24 hours later

#### Scenario: Expired story is not active
- **WHEN** a story's expiration timestamp has passed
- **THEN** the story is not returned as an active story for its owner, for any feed, and is removed from the stories bar

### Requirement: Story creation
The system SHALL allow a logged-in user to create a story via
`POST /stories/create/` without uploading a file; the system generates the
media automatically as a placeholder image. On success the response SHALL
render a success toast ("Story created") and an out-of-band re-render of the
stories bar. An unauthenticated request MUST be rejected.

#### Scenario: Successful web creation
- **WHEN** a logged-in user submits `POST /stories/create/`
- **THEN** the system creates a story with a generated placeholder image and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Unauthenticated creation rejected
- **WHEN** an anonymous client submits `POST /stories/create/`
- **THEN** the system rejects the request instead of creating a story

### Requirement: Stories bar on the home page
The home page of a logged-in user SHALL display a stories bar above the post
feed with two sections: a "Your story" button that creates a story, and one
avatar per followed user who has at least one active story, labeled with the
username and using the user's profile picture when present. Users the viewer
does not follow MUST NOT appear in the bar, even if they have active stories.

#### Scenario: Bar lists followed users with active stories
- **WHEN** a logged-in user visits the home page and a followed user has active stories
- **THEN** the stories bar shows one avatar for that user labeled with their username

#### Scenario: Bar excludes non-followed users
- **WHEN** a user who is not followed by the viewer has active stories
- **THEN** that user does not appear in the viewer's stories bar

#### Scenario: Bar empty without followings
- **WHEN** a logged-in user with no follows and no active stories of followees visits the home page
- **THEN** the stories bar shows only the "Your story" add button

### Requirement: Story view tracking
The system SHALL record a view when a logged-in user opens a followed user's
active story via `POST /stories/<uuid:story_id>/view/`; the response SHALL
render a success toast ("Story viewed") and an out-of-band updated stories
bar. A (story, viewer) pair SHALL be recorded at most once; marking the same
story again MUST NOT duplicate the record. A user MUST NOT record a view of
their own story. Stories of users the viewer does not follow MUST NOT be
viewable.

#### Scenario: First view recorded
- **WHEN** a logged-in user submits `POST /stories/<uuid>/view/` for a followed user's active story they have not seen
- **THEN** the system records the view once and renders a success toast plus an out-of-band updated stories bar

#### Scenario: Repeated view is idempotent
- **WHEN** the same user marks the same story as viewed again
- **THEN** no duplicate view record is created

#### Scenario: Self-view rejected
- **WHEN** a user submits `POST /stories/<uuid>/view/` for their own story
- **THEN** the system does not record a view and reports the error

#### Scenario: Non-followed story not viewable
- **WHEN** a logged-in user submits `POST /stories/<uuid>/view/` for a story owned by a user they do not follow
- **THEN** the system does not record the view

### Requirement: Stories bar ordering
The stories bar SHALL order followed-user groups so that groups whose latest
story is unviewed by the viewer come first, followed by groups whose latest
story is already viewed; within each group the member's stories keep their
creation order (newest first). After the viewer marks a story as viewed, the
group's ring state SHALL update to viewed on the next bar render.

#### Scenario: Unviewed groups first
- **WHEN** the viewer has an unviewed followed-user group and a viewed followed-user group
- **THEN** the unviewed group's avatar appears before the viewed group's avatar

#### Scenario: Ring updates after viewing
- **WHEN** the viewer marks the latest story of a group as viewed and the bar re-renders
- **THEN** that group's avatar is rendered with the viewed ring state

### Requirement: Expired story cleanup
The system SHALL delete expired stories together with their view records. The
home page render SHALL purge expired stories as a lazy cleanup, and a
management command SHALL purge them on demand, reporting how many stories were
deleted.

#### Scenario: Lazy purge on home render
- **WHEN** a logged-in user renders the home page while expired stories exist
- **THEN** the system deletes those expired stories and their view records before rendering

#### Scenario: Management command cleanup
- **WHEN** an operator runs the expired-stories cleanup management command
- **THEN** the system deletes all expired stories and reports the number deleted
