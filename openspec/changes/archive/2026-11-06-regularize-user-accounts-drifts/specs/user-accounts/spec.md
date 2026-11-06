# Spec Delta

## ADDED Requirements

### Requirement: API documentation surface
The system SHALL expose an OpenAPI schema at `/schema/` and a Swagger UI at
`/docs/`. The schema MUST include the register, login and token refresh
operations of the authentication API.

#### Scenario: OpenAPI schema is served
- **WHEN** a client requests `/schema/`
- **THEN** the system responds with the OpenAPI document including the `POST /api/auth/register/`, `POST /api/auth/login/` and `POST /api/auth/refresh/` operations

#### Scenario: Swagger UI is served
- **WHEN** a user opens `/docs/`
- **THEN** the system renders the Swagger UI listing the register, login and token refresh operations

### Requirement: Authenticated landing placeholder
The system SHALL serve a placeholder feed page at `/web/feed/` that requires
an authenticated session and acts as the landing page after web login. The
real feed capability is owned by a later change.

#### Scenario: Placeholder requires login
- **WHEN** an anonymous visitor requests `/web/feed/`
- **THEN** the system redirects to the login page

#### Scenario: Logged-in user reaches the placeholder
- **WHEN** a logged-in user requests `/web/feed/`
- **THEN** the system renders the placeholder page

## MODIFIED Requirements

### Requirement: User registration
The system SHALL allow a visitor to register an account with username, email
and password. Registration MUST fail with an explicit error when the email is
already registered ("Email already registered") or the username is already
taken ("Username already taken"). The password MUST be at least 8 characters
long. The system MUST NOT require the user to be logged in to register.
Storage MUST guarantee username and email uniqueness even under concurrent
registration attempts.

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

#### Scenario: Concurrent duplicate registration keeps data consistent
- **WHEN** two registration attempts for the same username or email race past the explicit duplicate check
- **THEN** storage accepts at most one account and never stores a duplicate username or email

### Requirement: API JWT login
The system SHALL expose `POST /api/auth/login/` accepting username and
password. On success it MUST respond 200 with the user data, an access token
with a 30 minute lifetime and a refresh token with a 1 day lifetime. On any
failure — including blank or missing fields — it MUST respond 401 with the
generic error "Invalid credentials".

#### Scenario: Successful API login
- **WHEN** a client posts correct credentials to `/api/auth/login/`
- **THEN** the system responds 200 with the user data, a JWT access token and a JWT refresh token

#### Scenario: Failed API login
- **WHEN** a client posts wrong credentials to `/api/auth/login/`
- **THEN** the system responds 401 with the error "Invalid credentials"

#### Scenario: API login with missing fields
- **WHEN** a client posts a login request with blank or missing username or password
- **THEN** the system responds 401 with the error "Invalid credentials" and never reveals which field is missing
