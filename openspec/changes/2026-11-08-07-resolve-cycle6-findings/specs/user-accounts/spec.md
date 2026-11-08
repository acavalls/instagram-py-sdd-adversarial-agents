# Spec Delta

## Purpose

Declares the two API trimming leniencies and the session-cookie auth
fallback that the cycle-6 audit found undeclared.

## MODIFIED Requirements

### Requirement: API registration
The system SHALL expose `POST /api/auth/register/` accepting username, email
and password. On success it MUST respond 201 with the user id, username,
email and bio. It MUST respond 409 when the email or username is already
registered and 400 when validation fails. The API endpoint SHALL trim
surrounding whitespace from the submitted email before validation and
storage; the stored email and its uniqueness remain byte-exact after the
trim. The username is never trimmed: a padded username is rejected with the
username validation error.

#### Scenario: Successful API registration
- **WHEN** a client posts valid registration data to `/api/auth/register/`
- **THEN** the system responds 201 with the created user data (id, email, username, bio, updated_at)

#### Scenario: API registration conflict
- **WHEN** a client posts registration data with an already registered email or an already taken username
- **THEN** the system responds 409 with the corresponding error message

#### Scenario: API registration validation error
- **WHEN** a client posts registration data that fails field validation (bad email, short username or short password)
- **THEN** the system responds 400 with field-level validation errors

#### Scenario: API registration trims the email whitespace
- **WHEN** a client posts registration data with an email carrying surrounding whitespace
- **THEN** the system trims the email before validation and storage, responds 201 and stores the trimmed value byte-exactly

### Requirement: API JWT login
The system SHALL expose `POST /api/auth/login/` accepting username and
password. On success it MUST respond 200 with the user data, an access token
with a 30 minute lifetime and a refresh token with a 1 day lifetime. On any
failure — including blank or missing fields — it MUST respond 401 with the
generic error "Invalid credentials". The endpoint SHALL trim surrounding
whitespace from the submitted username before authentication (an inert
leniency: no storage path can hold a padded username). API endpoints SHALL
also accept authenticated session cookies in addition to JWTs; this keeps
the browsable API documentation usable without a token.

#### Scenario: Successful API login
- **WHEN** a client posts correct credentials to `/api/auth/login/`
- **THEN** the system responds 200 with the user data, a JWT access token and a JWT refresh token

#### Scenario: Failed API login
- **WHEN** a client posts wrong credentials to `/api/auth/login/`
- **THEN** the system responds 401 with the error "Invalid credentials"

#### Scenario: API login with missing fields
- **WHEN** a client posts a login request with blank or missing username or password
- **THEN** the system responds 401 with the error "Invalid credentials" and never reveals which field is missing

#### Scenario: API login trims the username before authentication
- **WHEN** a client posts login credentials whose username carries surrounding whitespace and whose password is correct
- **THEN** the system trims the username before authentication and responds 200 with the tokens

#### Scenario: API endpoints accept session-cookie authentication
- **WHEN** a client with an authenticated web session (no JWT) requests an API endpoint that requires authentication
- **THEN** the endpoint accepts the session cookie and responds as an authenticated client
