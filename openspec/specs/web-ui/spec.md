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
entry links to the home feed; the Search, Explore, Messages, Notifications,
Create and Profile entries are placeholder links without a destination until
their capabilities land (Create is wired by the posts capability, Profile by
the social capability).

#### Scenario: Sidebar renders navigation for authenticated user
- **WHEN** a logged-in user renders any web page
- **THEN** the page shows the sidebar with the logo, Home, Search, Explore, Messages, Notifications, Create, Profile and logout entries

#### Scenario: Placeholder entries have no destination
- **WHEN** a logged-in user renders any web page
- **THEN** the Search, Explore, Messages, Notifications, Create and Profile entries are placeholder links without a destination page

#### Scenario: Logo links to the home feed
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar logo links to `/web/feed/`

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
