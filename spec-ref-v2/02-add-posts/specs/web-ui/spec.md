# Spec Delta

## Purpose

Extends the global web shell with the first real wiring (the sidebar Create
entry now creates posts) and defines the post card anatomy used by every
surface that renders posts.

## MODIFIED Requirements

### Requirement: Sidebar navigation
For a logged-in user, every web page SHALL render a fixed left sidebar with
the app logo linking to the home feed, navigation entries (Home, Search,
Explore, Messages, Notifications, Create, Profile) and a logout form at its
bottom. An anonymous visitor's pages MUST NOT render the sidebar. The Home
entry links to the home feed; the Create entry submits the random post
creation form to `POST /web/posts/create/`; the Search, Explore, Messages,
Notifications and Profile entries remain placeholder links without a
destination until their capabilities land.

#### Scenario: Sidebar renders navigation for authenticated user
- **WHEN** a logged-in user renders any web page
- **THEN** the page shows the sidebar with the logo, Home, Search, Explore, Messages, Notifications, Create, Profile and logout entries

#### Scenario: Placeholder entries have no destination
- **WHEN** a logged-in user renders any web page
- **THEN** the Search, Explore, Messages, Notifications and Profile entries are placeholder links without a destination page

#### Scenario: Logo links to the home feed
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar logo links to `/web/feed/`

#### Scenario: Create submits the post creation form
- **WHEN** a logged-in user activates the Create entry
- **THEN** the sidebar submits the random post creation form to `POST /web/posts/create/`

#### Scenario: Logout available at the sidebar bottom
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar bottom contains the logout form

#### Scenario: Anonymous pages render without sidebar
- **WHEN** an anonymous visitor opens the login page
- **THEN** the page renders the auth layout without the sidebar navigation

## ADDED Requirements

### Requirement: Post card anatomy
A post card SHALL render a header with the owner avatar and a username link
to the owner profile, the media (or an image placeholder icon when the post
has no media), an actions row with like, comment, share and save buttons, and
a content block with the caption prefixed by the owner username and the
relative creation time. The action buttons SHALL be presentational
placeholders without behavior. A post with multiple media files SHALL render
only its first media file. On the owner's own posts the card SHALL keep
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

#### Scenario: Multiple media renders the first file only
- **WHEN** a post card or grid item renders for a post with several media files
- **THEN** the UI shows only the first media file
