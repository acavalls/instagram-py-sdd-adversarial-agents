"""API view tests for registration and JWT auth, named after the spec scenarios.

Tasks 3.3 (registration), 5.1 (login) and 5.2 (token refresh).
"""

import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"

VALID_DATA = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "sup3r-secret-pw",
}


def test_successful_api_registration(api_client):
    response = api_client.post(REGISTER_URL, VALID_DATA)

    assert response.status_code == 201
    user = User.objects.get(username="alice")
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "alice@example.com"
    assert data["username"] == "alice"
    assert data["bio"] == ""
    assert "updated_at" in data
    # The password is never echoed back.
    assert "password" not in data
    assert user.password != VALID_DATA["password"]
    assert user.check_password(VALID_DATA["password"])


def test_api_registration_conflict(api_client):
    User.objects.create_user(username="bob", email="taken@example.com", password="password123")

    response = api_client.post(REGISTER_URL, {**VALID_DATA, "email": "taken@example.com"})
    assert response.status_code == 409
    assert response.json()["error"] == "Email already registered"

    response = api_client.post(REGISTER_URL, {**VALID_DATA, "username": "bob"})
    assert response.status_code == 409
    assert response.json()["error"] == "Username already taken"


def test_api_registration_validation_error(api_client):
    response = api_client.post(REGISTER_URL, {**VALID_DATA, "email": "not-an-email"})
    assert response.status_code == 400
    assert "email" in response.json()

    response = api_client.post(REGISTER_URL, {**VALID_DATA, "username": "ab"})
    assert response.status_code == 400
    assert "username" in response.json()

    response = api_client.post(REGISTER_URL, {**VALID_DATA, "username": "al!"})
    assert response.status_code == 400
    assert response.json()["username"] == ["Username must contain only letters and numbers"]

    response = api_client.post(REGISTER_URL, {**VALID_DATA, "password": "short"})
    assert response.status_code == 400
    assert response.json()["password"] == ["Password must be at least 8 characters"]

    # Nothing was created by the rejected attempts.
    assert not User.objects.filter(username="alice").exists()


def test_successful_api_login(api_client):
    User.objects.create_user(
        username="alice", email="alice@example.com", password="sup3r-secret-pw"
    )

    response = api_client.post(LOGIN_URL, {"username": "alice", "password": "sup3r-secret-pw"})

    assert response.status_code == 200
    user = User.objects.get(username="alice")
    data = response.json()
    # The user data mirrors the register response shape.
    assert data["id"] == str(user.id)
    assert data["email"] == "alice@example.com"
    assert data["username"] == "alice"
    assert data["bio"] == ""
    assert "updated_at" in data
    assert "password" not in data
    # Both JWT tokens are issued, and the access token carries the user id claim.
    access = AccessToken(data["access"])
    assert access["user_id"] == str(user.id)
    refresh = RefreshToken(data["refresh"])
    assert refresh["user_id"] == str(user.id)


def test_failed_api_login(api_client):
    User.objects.create_user(
        username="alice", email="alice@example.com", password="sup3r-secret-pw"
    )

    # Wrong password.
    response = api_client.post(LOGIN_URL, {"username": "alice", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid credentials"

    # Unknown username answers the same generic error (the cause is never revealed).
    response = api_client.post(LOGIN_URL, {"username": "nobody", "password": "sup3r-secret-pw"})
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid credentials"


def test_api_login_with_missing_fields(api_client):
    """Scenario: API login with missing fields — blank or missing username or
    password answers the same generic 401, never revealing which field is
    missing."""
    User.objects.create_user(
        username="alice", email="alice@example.com", password="sup3r-secret-pw"
    )

    attacks = [
        {"username": "", "password": "sup3r-secret-pw"},  # blank username
        {"username": "alice", "password": ""},  # blank password
        {"username": "alice"},  # missing password
        {"password": "sup3r-secret-pw"},  # missing username
        {},  # everything missing
    ]
    for payload in attacks:
        response = api_client.post(LOGIN_URL, payload)
        assert response.status_code == 401, payload
        # Identical generic body for every failure shape: no field hints.
        assert response.json() == {"error": "Invalid credentials"}, payload


def test_password_with_surrounding_spaces_round_trips_api(api_client):
    """Spec scenario 'Password comparison is byte-exact' (User account data,
    openspec/changes/regularize-social-drifts/specs/user-accounts/spec.md).
    The API never trims the password (DRIFT-012): a password registered
    with surrounding spaces is stored byte-exactly and only authenticates
    with those same spaces — the trimmed variant fails at login."""
    padded_password = " sup3r-secret-pw "

    register = api_client.post(
        REGISTER_URL,
        {"username": "alice", "email": "alice@example.com", "password": padded_password},
    )
    assert register.status_code == 201
    user = User.objects.get(username="alice")
    assert user.check_password(padded_password)

    login = api_client.post(LOGIN_URL, {"username": "alice", "password": padded_password})
    assert login.status_code == 200

    # The trimmed variant is a different credential and must fail.
    trimmed_login = api_client.post(
        LOGIN_URL, {"username": "alice", "password": padded_password.strip()}
    )
    assert trimmed_login.status_code == 401


def test_successful_token_refresh(api_client):
    user = User.objects.create_user(
        username="alice", email="alice@example.com", password="sup3r-secret-pw"
    )
    refresh_token = RefreshToken.for_user(user)

    response = api_client.post(REFRESH_URL, {"refresh": str(refresh_token)})

    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    # The new access token is a valid JWT carrying the user id claim.
    access = AccessToken(data["access"])
    assert access["user_id"] == str(user.id)


def test_invalid_refresh_token_rejected(api_client):
    # Missing refresh token: rejected without issuing any access token.
    response = api_client.post(REFRESH_URL, {})
    assert response.status_code == 400
    assert "access" not in response.json()

    # Invalid/garbage refresh token: rejected without issuing any access token.
    response = api_client.post(REFRESH_URL, {"refresh": "not-a-jwt"})
    assert response.status_code == 401
    assert "access" not in response.json()
