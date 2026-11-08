# web-ui Specification

## Purpose
The global web shell: how every authenticated page is framed (sidebar
navigation) and how authentication pages are presented (dedicated auth
layout). Covers navigation structure, active states, icon rendering and the
auth presentation, not the content inside the pages. Entries whose
capabilities do not exist yet are declared placeholder links; later packages
wire them in without introducing navigation after the fact.

## Requirements

### Requirement: Sidebar navigation
For a logged-in user, every web page SHALL render a fixed left sidebar with
the app logo linking to the home feed, navigation entries (Home, Search,
Explore, Messages, Notifications, Create, Profile) and a logout form at its
bottom. An anonymous visitor's pages MUST NOT render the sidebar. The Home
entry links to the home feed; the Create entry submits the random post
creation form to `POST /web/posts/create/`; the Profile entry links to the
logged-in user's own profile page; the Search, Explore, Messages and
Notifications entries remain placeholder links without a destination.

#### Scenario: Sidebar renders navigation for authenticated user
- **WHEN** a logged-in user renders any web page
- **THEN** the page shows the sidebar with the logo, Home, Search, Explore, Messages, Notifications, Create, Profile and logout entries

#### Scenario: Placeholder entries have no destination
- **WHEN** a logged-in user renders any web page
- **THEN** the Search, Explore, Messages and Notifications entries are placeholder links without a destination page

#### Scenario: Logo links to the home feed
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar logo links to `/web/feed/`

#### Scenario: Create submits the post creation form
- **WHEN** a logged-in user activates the Create entry
- **THEN** the sidebar submits the random post creation form to `POST /web/posts/create/`

#### Scenario: Profile link points to own profile
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar Profile link points to `/web/profile/<their id>/`

#### Scenario: Logout available at the sidebar bottom
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar bottom contains the logout form

#### Scenario: Anonymous pages render without sidebar
- **WHEN** an anonymous visitor opens the login page
- **THEN** the page renders the auth layout without the sidebar navigation

### Requirement: Active navigation state
The sidebar entry of the page currently rendered SHALL be highlighted as
active, and the other entries SHALL NOT be.

#### Scenario: Active link reflects current page
- **WHEN** a logged-in user renders the home feed
- **THEN** the Home entry is marked active and the other entries are not

### Requirement: Icon rendering
Every web page SHALL load the Bootstrap Icons stylesheet so that `bi-*` icon
classes render visually.

#### Scenario: Icon font is loaded
- **WHEN** any web page renders
- **THEN** the response includes the Bootstrap Icons stylesheet link

### Requirement: Auth layout
The login and register pages SHALL render in a dedicated auth layout: an
`auth-page` body with a centered auth card showing the app logo and the
form, a secondary card linking to the counterpart page, and footer links.
The auth layout MUST NOT include the authenticated app sidebar.

#### Scenario: Login renders the auth card
- **WHEN** a visitor opens the login page
- **THEN** the page renders an auth card with the logo and the login form, plus a secondary card linking to the register page

#### Scenario: Register renders the auth card
- **WHEN** a visitor opens the register page
- **THEN** the page renders an auth card with the logo and the register form, plus a secondary card linking to the login page

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

### Requirement: Profile page structure
A profile page SHALL render a header with a large avatar, the username, a
follow button on other profiles, a stats row (posts, followers, following —
the following stat opens the following-list modal), and a tabs bar with
POSTS active and SAVED and TAGGED as placeholders. Grid items SHALL show the
post media with a hover overlay; a post with multiple media files SHALL
render only its first media file. The tabs SHALL be presentational
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
