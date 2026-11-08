# Spec Delta

## Purpose

Declares the session-precedence/CSRF semantics and the anonymous-403
surface (C7-02, C7-03), completing the API auth contract.

## MODIFIED Requirements

### Requirement: API JWT login
The system SHALL expose `POST /api/auth/login/` accepting username and
password. On success it MUST respond 200 with the user data, an access token
with a 30 minute lifetime and a refresh token with a 1 day lifetime. On any
failure — including blank or missing fields — it MUST respond 401 with the
generic error "Invalid credentials". The endpoint SHALL trim surrounding
whitespace from the submitted username before authentication (an inert
leniency: no storage path can hold a padded username). API endpoints SHALL
also accept authenticated session cookies in addition to JWTs; this keeps
the browsable API documentation usable without a token. When a request
carries both an authenticated session cookie and a JWT, the session identity
wins; unsafe (non-GET) requests authenticated by session cookie MUST satisfy
CSRF protection and are rejected otherwise. API endpoints guarded by
authentication MUST reject anonymous requests with 403 and no
`WWW-Authenticate` challenge header.

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

#### Scenario: Session identity wins over a presented JWT
- **WHEN** a request carries an authenticated session cookie of one user and a valid JWT of a different user
- **THEN** the endpoint acts as the session's user

#### Scenario: CSRF is enforced on session-authenticated unsafe methods
- **WHEN** a session-authenticated client sends an unsafe (non-GET) API request without a valid CSRF token
- **THEN** the request is rejected and no action is performed

#### Scenario: Anonymous requests are rejected without a challenge
- **WHEN** an anonymous client requests an API endpoint guarded by authentication
- **THEN** the system responds 403 with no `WWW-Authenticate` header
