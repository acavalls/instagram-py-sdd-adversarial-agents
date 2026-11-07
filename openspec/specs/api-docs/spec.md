# api-docs Specification

## Purpose

Exposes the REST API contract as an OpenAPI schema and an interactive
Swagger UI, so clients can discover and try the endpoints.

## Requirements

### Requirement: OpenAPI documentation
The system SHALL serve an OpenAPI schema of the public API at `/schema/`
(JSON with `?format=json`, YAML by default) and a Swagger UI at `/docs/`
that lists the registered API endpoints.

#### Scenario: Schema endpoint serves the API contract
- **WHEN** a client requests `/schema/?format=json`
- **THEN** the system responds 200 with an OpenAPI document including the authentication and posts paths

#### Scenario: Docs UI renders
- **WHEN** a user opens `/docs/`
- **THEN** the system responds 200 with the Swagger UI page
