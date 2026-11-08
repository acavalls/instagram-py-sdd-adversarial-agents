# Spec Delta

## Purpose

Declares the contracts that five cycles of implementation and testing left
pinned only by code: the save() silent-refusal rule, hashed passwords on
every storage path, the authenticated-login-page redirect, and the
byte-exact whitespace-rejecting username and email rules.

## MODIFIED Requirements

### Requirement: User account data
The system SHALL store a user account with a unique username, a unique email,
an optional bio, an optional profile picture and a hashed password. The
username MUST contain only alphanumeric characters and MUST be between 3 and
150 characters long. The username rule MUST hold on every storage path,
including queryset bulk operations: a bulk write carrying a legal username
MUST apply it, a bulk write carrying a username that violates the rule MUST
be refused with the model's username validation error, and a bulk write
carrying a non-literal username value (an expression or missing value with
no text to validate) MUST be refused with the same error. A direct save()
carrying an invalid username MUST refuse the write silently: no exception is
raised to the caller and nothing is stored. Passwords MUST be hashed on
every storage path: objects created or bulk-created with a raw password MUST
end up storing only a hash that authenticates against that password, never
the raw value. Passwords MUST be compared and stored byte-exactly, without
whitespace trimming or case folding. Usernames MUST be rejected when they
carry surrounding whitespace, on every registration path, without trimming.
Email uniqueness MUST be byte-exact and case-sensitive.

#### Scenario: User account persisted
- **GIVEN** a user completes registration with valid data
- **THEN** the system stores a user with UUID identifier, unique username, unique email, optional bio, optional profile picture and a hashed (never plain-text) password

#### Scenario: Username format validation
- **WHEN** a registration attempt uses a username shorter than 3 characters, longer than 150 characters, or containing non-alphanumeric characters
- **THEN** the system rejects the registration with the error "Username must contain only letters and numbers" or an equivalent length error

#### Scenario: Bulk writes enforce the username rule
- **WHEN** a bulk write (queryset update, bulk create or bulk update) carries a username that violates the username rule
- **THEN** the system rejects the write with the model's username validation error instead of storing the invalid username

#### Scenario: Non-literal username write refused
- **WHEN** a queryset update or bulk create carries a non-literal username value (an expression or a value with no text to validate)
- **THEN** the system refuses the whole write with the model's username validation error

#### Scenario: Legal username bulk write applies
- **WHEN** a bulk update or bulk create carries a literal username that satisfies the username rule
- **THEN** the system writes the new username and the write succeeds

#### Scenario: Password comparison is byte-exact
- **WHEN** credentials are checked for login or token issuance
- **THEN** the system compares the submitted password byte-exactly, without trimming whitespace or folding case

#### Scenario: Direct save refuses an invalid username silently
- **WHEN** a user instance with a username that violates the username rule is saved directly
- **THEN** the system refuses the write silently: no exception is raised to the caller and nothing is stored

#### Scenario: Bulk paths store hashed passwords
- **WHEN** users are created or bulk-created with a raw password
- **THEN** the stored value is a hash that authenticates against that password, and the raw value is never stored

#### Scenario: Padded usernames are rejected on every registration path
- **WHEN** a registration attempt (web or API) uses a username with surrounding whitespace
- **THEN** the system rejects the registration with the username validation error, without trimming the value

#### Scenario: Email uniqueness is byte-exact
- **WHEN** a registration attempt uses an email that differs from an existing user's email only by letter case
- **THEN** the system accepts the registration, because email uniqueness is case-sensitive

### Requirement: Web session login
The system SHALL allow a user to log in from the web UI with username and
password. On success the system MUST create a session, redirect the user to
the feed page and confirm with "Logged in successfully". On failure the
system MUST show a single generic error ("Invalid credentials") without
revealing whether the username or the password was wrong. An
already-authenticated visitor requesting the login page MUST be redirected
to the feed.

#### Scenario: Successful web login
- **WHEN** a registered user submits the login form with correct username and password
- **THEN** the system creates a session, redirects to the feed page and shows the toast "Logged in successfully"

#### Scenario: Failed web login hides the cause
- **WHEN** a user submits the login form with a wrong password (or an unknown username)
- **THEN** the system re-renders the login page with the error "Invalid credentials" and does not reveal which field was wrong

#### Scenario: Authenticated visitor is redirected to the feed
- **WHEN** an already-authenticated user requests the login page
- **THEN** the system redirects to the feed instead of rendering the login form again
