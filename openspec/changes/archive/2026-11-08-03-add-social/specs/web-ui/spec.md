# Spec Delta

## Purpose

Wires the last feature-dependent sidebar placeholder (Profile) and adds the
profile page structure used by the social capability.

## MODIFIED Requirements

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

## ADDED Requirements

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
