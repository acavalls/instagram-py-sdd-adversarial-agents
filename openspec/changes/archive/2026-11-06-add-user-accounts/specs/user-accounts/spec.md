# Spec Delta

## Purpose

Lets a person create an identity in the app and prove it, both from the web
UI (session) and from the REST API (JWT). It owns user registration rules
and authentication behavior; everything that attaches content or social
relationships to a user builds on this capability.

## ADDED Requirements

### Requirement: User account data
The system SHALL store a user account with a unique username, a unique email,
an optional bio, an optional profile picture and a hashed password. The
username MUST contain only alphanumeric characters and MUST be between 3 and
150 characters long.

#### Scenario: User account persisted
- **GIVEN** a user completes registration with valid data
- **THEN** the system stores a user with UUID identifier, unique username, unique email, optional bio, optional profile picture and a hashed (never plain-text) password

#### Scenario: Username format validation
- **WHEN** a registration attempt uses a username shorter than 3 characters, longer than 150 characters, or containing non-alphanumeric characters
- **THEN** the system rejects the registration with the error "Username must contain only letters and numbers" or an equivalent length error

### Requirement: User registration
The system SHALL allow a visitor to register an account with username, email
and password. Registration MUST fail with an explicit error when the email is
already registered ("Email already registered") or the username is already
taken ("Username already taken"). The password MUST be at least 8 characters
long. The system MUST NOT require the user to be logged in to register.

#### Scenario: Successful registration
- **WHEN** a visitor submits registration with a new email, a new valid username and a password of at least 8 characters
- **THEN** the system creates the account and, on the web UI, redirects to the login page with the confirmation "Account created successfully. Please login."

#### Scenario: Duplicate email rejected
- **WHEN** a visitor submits registration with an email that is already registered
- **THEN** the system rejects the registration with the error "Email already registered"

#### Scenario: Duplicate username rejected
- **WHEN** a visitor submits registration with a username that is already taken
- **THEN** the system rejects the registration with the error "Username already taken"

#### Scenario: Password too short rejected
- **WHEN** a visitor submits registration with a password shorter than 8 characters
- **THEN** the system rejects the registration with the error "Password must be at least 8 characters"

### Requirement: Web session login
The system SHALL allow a user to log in from the web UI with username and
password. On success the system MUST create a session, redirect the user to
the feed page and confirm with "Logged in successfully". On failure the
system MUST show a single generic error ("Invalid credentials") without
revealing whether the username or the password was wrong.

#### Scenario: Successful web login
- **WHEN** a registered user submits the login form with correct username and password
- **THEN** the system creates a session, redirects to the feed page and shows the toast "Logged in successfully"

#### Scenario: Failed web login hides the cause
- **WHEN** a user submits the login form with a wrong password (or an unknown username)
- **THEN** the system re-renders the login page with the error "Invalid credentials" and does not reveal which field was wrong

### Requirement: Web session logout
The system SHALL allow a logged-in user to log out from the web UI. Logging
out MUST clear the session, redirect to the login page and confirm with "You
have been logged out".

#### Scenario: Successful logout
- **WHEN** a logged-in user requests logout
- **THEN** the system clears the session, redirects to the login page and shows "You have been logged out"

#### Scenario: Protected pages require login
- **WHEN** an anonymous visitor requests a page that requires authentication
- **THEN** the system redirects to the login page

### Requirement: API registration
The system SHALL expose `POST /api/auth/register/` accepting username, email
and password. On success it MUST respond 201 with the user id, username,
email and bio. It MUST respond 409 when the email or username is already
registered and 400 when validation fails.

#### Scenario: Successful API registration
- **WHEN** a client posts valid registration data to `/api/auth/register/`
- **THEN** the system responds 201 with the created user data (id, email, username, bio, updated_at)

#### Scenario: API registration conflict
- **WHEN** a client posts registration data with an already registered email or an already taken username
- **THEN** the system responds 409 with the corresponding error message

#### Scenario: API registration validation error
- **WHEN** a client posts registration data that fails field validation (bad email, short username or short password)
- **THEN** the system responds 400 with field-level validation errors

### Requirement: API JWT login
The system SHALL expose `POST /api/auth/login/` accepting username and
password. On success it MUST respond 200 with the user data, an access token
and a refresh token. On failure it MUST respond 401 with the generic error
"Invalid credentials".

#### Scenario: Successful API login
- **WHEN** a client posts correct credentials to `/api/auth/login/`
- **THEN** the system responds 200 with the user data, a JWT access token and a JWT refresh token

#### Scenario: Failed API login
- **WHEN** a client posts wrong credentials to `/api/auth/login/`
- **THEN** the system responds 401 with the error "Invalid credentials"

### Requirement: API token refresh
The system SHALL allow a client to exchange a valid refresh token for a new
access token. A missing, expired or invalid refresh token MUST be rejected
without issuing a new access token.

#### Scenario: Successful token refresh
- **WHEN** a client posts a valid refresh token to the token refresh endpoint
- **THEN** the system responds 200 with a new access token

#### Scenario: Invalid refresh token rejected
- **WHEN** a client posts a missing, expired or invalid refresh token
- **THEN** the system rejects the request without issuing an access token
