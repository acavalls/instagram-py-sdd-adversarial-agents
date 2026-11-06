# Spec Delta

## Purpose

The global web shell: how every authenticated page is framed (sidebar
navigation) and how authentication pages are presented (dedicated auth
layout). Covers navigation structure, active states, icon rendering and the
auth presentation, not the content inside the pages.

## ADDED Requirements

### Requirement: Sidebar navigation
For a logged-in user, every web page SHALL render a fixed left sidebar with
the app logo linking to the home feed, navigation entries (Home, Search,
Explore, Messages, Notifications, Create, Profile) and a logout form at its
bottom. An anonymous visitor's pages MUST NOT render the sidebar.

#### Scenario: Sidebar renders navigation for authenticated user
- **WHEN** a logged-in user renders any web page
- **THEN** the page shows the sidebar with the logo, Home, Search, Explore, Messages, Notifications, Create, Profile and logout entries

#### Scenario: Profile link points to own profile
- **WHEN** a logged-in user renders any web page
- **THEN** the sidebar Profile link points to `/web/profile/<their id>/`

#### Scenario: Placeholder entries have no destination
- **WHEN** a logged-in user renders any web page
- **THEN** the Search, Explore, Messages and Notifications entries are placeholder links without a destination page

#### Scenario: Create submits the post creation form
- **WHEN** a logged-in user activates the Create entry
- **THEN** the sidebar submits the random post creation form to `POST /web/posts/create/`

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
