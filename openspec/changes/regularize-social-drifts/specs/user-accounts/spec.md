# Spec Delta — user-accounts (MODIFIED)

## MODIFIED Requirements

### Requirement: User account data
The system SHALL store a user account with a unique username, a unique email,
an optional bio, an optional profile picture and a hashed password. The
username MUST contain only alphanumeric characters and MUST be between 3 and
150 characters long. The username rule MUST hold on every storage path,
including queryset bulk operations. Passwords MUST be compared and stored
byte-exactly, without whitespace trimming or case folding.

#### Scenario: User account persisted
- **GIVEN** a user completes registration with valid data
- **THEN** the system stores a user with UUID identifier, unique username, unique email, optional bio, optional profile picture and a hashed (never plain-text) password

#### Scenario: Username format validation
- **WHEN** a registration attempt uses a username shorter than 3 characters, longer than 150 characters, or containing non-alphanumeric characters
- **THEN** the system rejects the registration with the error "Username must contain only letters and numbers" or an equivalent length error

#### Scenario: Bulk writes enforce the username rule
- **WHEN** a bulk write (queryset update or bulk create) stores a username that violates the username rule
- **THEN** the system rejects the write with a validation error instead of storing the invalid username

#### Scenario: Password comparison is byte-exact
- **WHEN** credentials are checked for login or token issuance
- **THEN** the system compares the submitted password byte-exactly, without trimming whitespace or folding case

### Requirement: Web session logout
The system SHALL allow a logged-in user to log out from the web UI. Logging
out MUST clear the session, redirect to the login page and confirm with "You
have been logged out". Logout MUST be a POST-only action: non-POST requests
MUST respond 405 without clearing the session.

#### Scenario: Successful logout
- **WHEN** a logged-in user requests logout
- **THEN** the system clears the session, redirects to the login page and shows "You have been logged out"

#### Scenario: Protected pages require login
- **WHEN** an anonymous visitor requests a page that requires authentication
- **THEN** the system redirects to the login page

#### Scenario: Logout is POST-only
- **WHEN** a logged-in user sends a GET (or other non-POST) request to the logout endpoint
- **THEN** the system responds 405 and the session stays active
