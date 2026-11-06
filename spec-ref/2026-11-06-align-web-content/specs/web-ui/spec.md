# Spec Delta

## ADDED Requirements

### Requirement: Post card anatomy
A post card SHALL render a header with the owner avatar and a username link
to the owner profile, the media (or an image placeholder icon when the post
has no media), an actions row with like, comment, share and save buttons, and
a content block with the caption prefixed by the owner username and the
relative creation time. The action buttons SHALL be presentational
placeholders without behavior. On the owner's own posts the card SHALL keep
the edit and delete menu.

#### Scenario: Card header shows owner avatar and username link
- **WHEN** a post card renders
- **THEN** the header shows the owner avatar and the owner username linked to their profile page

#### Scenario: Card actions row renders placeholders
- **WHEN** a post card renders
- **THEN** the actions row shows like, comment, share and save buttons with no destination

#### Scenario: Missing media renders the placeholder icon
- **WHEN** a post card renders for a post without media
- **THEN** the media area shows the image placeholder icon instead of a broken image

### Requirement: Profile page structure
A profile page SHALL render a header with a large avatar, the username, a
follow button on other profiles, a stats row (posts, followers, following —
the following stat opens the following-list modal), and a tabs bar with
POSTS active and SAVED and TAGGED as placeholders. Grid items SHALL show the
post media with a hover overlay. The tabs SHALL be presentational
placeholders except POSTS.

#### Scenario: Profile header shows avatar, stats and tabs
- **WHEN** a logged-in user renders a profile page
- **THEN** the page shows the large avatar, the username, the posts/followers/following stats and the tabs bar with POSTS active

#### Scenario: Following stat opens the modal
- **WHEN** a logged-in user renders a profile page
- **THEN** the following stat links to the following-list modal endpoint

#### Scenario: Grid item shows overlay
- **WHEN** a profile grid item renders
- **THEN** the item shows the post media with a hover overlay
