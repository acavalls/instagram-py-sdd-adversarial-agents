# Spec Delta

## Purpose

Declares the profile grid's full-card anatomy (the design decision of
03-add-social) that the original delta wording described too narrowly.

## MODIFIED Requirements

### Requirement: Profile page structure
A profile page SHALL render a header with a large avatar, the username, a
follow button on other profiles, a stats row (posts, followers, following —
the following stat opens the following-list modal), and a tabs bar with
POSTS active and SAVED and TAGGED as placeholders. Grid items SHALL render
the full post-card anatomy — the card header (owner avatar and username
linked to the owner's profile), the post's media with a hover overlay, the
caption and the actions row — with edit and delete controls on the owner's
own items; a post with multiple media files SHALL render only its first
media file. The tabs SHALL be presentational placeholders except POSTS.

#### Scenario: Profile header shows avatar, stats and tabs
- **WHEN** a logged-in user renders a profile page
- **THEN** the page shows the large avatar, the username, the posts/followers/following stats and the tabs bar with POSTS active

#### Scenario: Following stat opens the modal
- **WHEN** a logged-in user renders a profile page
- **THEN** the following stat links to the following-list modal endpoint

#### Scenario: Grid item shows overlay
- **WHEN** a profile grid item renders
- **THEN** the item shows the post media with a hover overlay

#### Scenario: Grid item shows the post card anatomy
- **WHEN** a profile grid item renders
- **THEN** the item shows the card header (owner avatar and username linked to the owner's profile), the caption and the actions row, with edit and delete controls on the owner's own items
