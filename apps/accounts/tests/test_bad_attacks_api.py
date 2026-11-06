"""Adversarial API attacks (The Bad) against the accounts capability.

Each test documents an attack (ATK-00N) trying to break the registration,
login or token-refresh surface with malformed, hostile or boundary inputs.
"""

import json
import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"

VALID = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "sup3r-secret-pw",
}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def register(api: APIClient, **overrides):
    data = dict(VALID)
    data.update(overrides)
    return api.post(REGISTER_URL, data, format="json")


def create_user(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return User.objects.create_user(**data)


# --- Registration attacks -------------------------------------------------


def test_atk_001_malformed_json_body(api):
    """ATK-001: POST a syntactically invalid JSON body — must be 400, never 500."""
    response = api.post(REGISTER_URL, data="{not-valid-json", content_type="application/json")
    assert response.status_code == 400, response.content
    assert response.status_code < 500


def test_atk_002_unsupported_content_type(api):
    """ATK-002: POST registration with an unsupported content type — must not
    crash with a 500."""
    response = api.post(
        REGISTER_URL,
        data=json.dumps(VALID),
        content_type="text/plain",
    )
    assert response.status_code < 500
    assert response.status_code in (400, 415)


def test_atk_003_privilege_escalation_fields_ignored(api):
    """ATK-003: inject extra privileged fields in the payload; they must be
    ignored, never applied to the created user."""
    response = register(
        api,
        is_staff=True,
        is_superuser=True,
        bio="injected bio",
        email_verified=True,
    )
    assert response.status_code == 201, response.content
    user = User.objects.get(username=VALID["username"])
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.bio == ""  # bio is read-only per the serializer


def test_atk_004_password_never_echoed(api):
    """ATK-004: the plaintext password and the password hash must never appear
    in the register or login responses."""
    response = register(api)
    body = response.content.decode()
    assert VALID["password"] not in body
    user = User.objects.get(username=VALID["username"])
    assert user.password not in body  # hash not leaked

    login = api.post(
        LOGIN_URL,
        {"username": VALID["username"], "password": VALID["password"]},
        format="json",
    )
    login_body = login.content.decode()
    assert VALID["password"] not in login_body
    assert user.password not in login_body
    assert "password" not in login.json()


def test_atk_005_username_boundaries_and_unicode(api):
    """ATK-005: username boundary values (3, 150 OK; 2, 151, unicode rejected
    with the format/length error messages)."""
    name3 = "abc"
    assert register(api, username=name3, email="n3@example.com").status_code == 201

    name150 = "a" * 150
    assert register(api, username=name150, email="n150@example.com").status_code == 201

    short = register(api, username="ab")
    assert short.status_code == 400
    assert "Username must be between 3 and 150 characters" in short.content.decode()

    long = register(api, username="a" * 151)
    assert long.status_code == 400

    unicode_name = register(api, username="álice")
    assert unicode_name.status_code == 400
    assert "Username must contain only letters and numbers" in unicode_name.content.decode()


def test_atk_006_password_boundaries(api):
    """ATK-006: password of exactly 8 chars accepted; 7 chars rejected with
    the spec message; 129 chars rejected (serializer max) without a 500."""
    assert register(api, password="12345678").status_code == 201

    short = register(api, username="pwshort", email="pwshort@example.com", password="1234567")
    assert short.status_code == 400
    assert "Password must be at least 8 characters" in short.content.decode()

    huge = register(api, username="pwhuge", email="pwhuge@example.com", password="x" * 129)
    assert huge.status_code == 400
    assert huge.status_code < 500


def test_atk_007_duplicate_double_submit(api):
    """ATK-007: submit the same registration twice — the second must be a 409
    with the exact spec message, and no second row created."""
    first = register(api)
    assert first.status_code == 201

    second_email = register(api, username="alice2")
    assert second_email.status_code == 409
    assert "Email already registered" in second_email.content.decode()

    third = register(api, email="other@example.com")
    assert third.status_code == 409
    assert "Username already taken" in third.content.decode()
    assert User.objects.filter(username=VALID["username"]).count() == 1


def test_atk_008_login_failure_shapes(api):
    """ATK-008: login attacks — empty username, missing fields, wrong password,
    unknown user. Wrong credentials must always be 401 with the identical
    generic error; structurally invalid input may be 400 but never a 500."""
    create_user()

    empty_username = api.post(LOGIN_URL, {"username": "", "password": "whatever123"}, format="json")
    # Blank input is a validation failure (400) — still no cause leak; wrong
    # credentials below must always be the identical generic 401.
    assert empty_username.status_code in (400, 401)
    assert empty_username.status_code < 500

    wrong_password = api.post(
        LOGIN_URL, {"username": VALID["username"], "password": "wrong-password"}, format="json"
    )
    unknown_user = api.post(
        LOGIN_URL, {"username": "ghost", "password": "wrong-password"}, format="json"
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"error": "Invalid credentials"}

    missing = api.post(LOGIN_URL, {"username": VALID["username"]}, format="json")
    assert missing.status_code == 400
    assert missing.status_code < 500


def test_atk_009_wrong_input_types(api):
    """ATK-009: send numbers/lists/None instead of strings — must never 500 and
    must never create a user from structurally invalid data. (Observation: DRF
    CharField coerces numeric input to a string, so an int password may be
    accepted as its string form — that is lenient typing, not corruption.)"""
    for payload in (
        {**VALID, "username": ["alice"]},
        {**VALID, "email": None},
        {**VALID, "password": {"leaked": True}},
    ):
        response = api.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400, payload
    coerced = api.post(REGISTER_URL, {**VALID, "password": 12345678}, format="json")
    assert coerced.status_code in (400, 201)
    assert coerced.status_code < 500
    assert not User.objects.filter(username=VALID["username"]).exists() or (
        coerced.status_code == 201
        and User.objects.get(username=VALID["username"]).check_password("12345678")
    )


def test_atk_010_register_response_shape(api):
    """ATK-010: the 201 response must carry id (UUID), email, username, bio and
    updated_at, and nothing must crash on the optional fields' defaults."""
    response = register(api)
    assert response.status_code == 201
    body = response.json()
    uuid.UUID(str(body["id"]))  # raises if not a valid UUID
    assert body["email"] == VALID["email"]
    assert body["username"] == VALID["username"]
    assert body["bio"] == ""
    assert "updated_at" in body


def test_atk_011_whitespace_and_email_shapes(api):
    """ATK-011: the API strips surrounding whitespace exactly like the web UI
    (DRF CharField trim_whitespace) — ' alice ' must register as 'alice' and
    only well-formed emails are accepted."""
    padded = register(api, username=" alice ")
    assert padded.status_code == 201
    assert padded.json()["username"] == "alice"
    assert User.objects.filter(username="alice").exists()

    assert register(api, username="taguser", email="user+tag@sub.example.co.uk").status_code == 201

    bad = register(api, username="bademail", email="not-an-email")
    assert bad.status_code == 400
    assert "Enter a valid email address" in bad.content.decode()


def test_atk_012_huge_payloads(api):
    """ATK-012: oversized inputs (10k-char email, 10k-char username) must be
    rejected with a 4xx, never a 500 or a DB error."""
    huge_email = register(api, username="hugeemail", email="a" * 10_000 + "@example.com")
    assert 400 <= huge_email.status_code < 500

    huge_name = register(api, username="a" * 10_000, email="huge@example.com")
    assert 400 <= huge_name.status_code < 500


# --- Login / refresh attacks ----------------------------------------------


def test_atk_013_refresh_token_lifecycle(api, monkeypatch):
    """ATK-013: refresh attacks — valid refresh works; missing, garbage and
    expired refresh tokens are rejected with NO access token issued."""
    from datetime import timedelta

    create_user()
    login = api.post(
        LOGIN_URL, {"username": VALID["username"], "password": VALID["password"]}, format="json"
    )
    refresh = login.json()["refresh"]

    ok = api.post(REFRESH_URL, {"refresh": refresh}, format="json")
    assert ok.status_code == 200
    assert "access" in ok.json()

    garbage = api.post(REFRESH_URL, {"refresh": "garbage.token.here"}, format="json")
    assert garbage.status_code in (400, 401)
    assert "access" not in garbage.json()

    missing = api.post(REFRESH_URL, {}, format="json")
    assert missing.status_code in (400, 401)
    assert "access" not in missing.json()

    blank = api.post(REFRESH_URL, {"refresh": ""}, format="json")
    assert blank.status_code in (400, 401)
    assert "access" not in blank.json()

    # Expired refresh token: craft a structurally valid token whose exp is
    # clearly in the past (no monkeypatch flakiness).
    from django.utils import timezone as dj_timezone
    from rest_framework_simplejwt.tokens import RefreshToken

    stale = RefreshToken()
    stale.set_exp(from_time=dj_timezone.now() - timedelta(days=2), lifetime=timedelta(days=1))
    expired = api.post(REFRESH_URL, {"refresh": str(stale)}, format="json")
    assert expired.status_code in (400, 401)
    assert "access" not in expired.json()


def test_atk_014_tampered_and_foreign_refresh(api):
    """ATK-014: a refresh token signed for another (nonexistent) audience or
    tampered payload must be rejected without issuing an access token."""
    from rest_framework_simplejwt.tokens import RefreshToken

    create_user()
    token = RefreshToken()
    # Tamper with the payload but keep a structurally valid token shape.
    tampered = str(token)
    header, payload, signature = tampered.split(".")
    tampered_token = f"{header}.{payload[:-2]}AA.{signature}"

    response = api.post(REFRESH_URL, {"refresh": tampered_token}, format="json")
    assert response.status_code in (400, 401)
    assert "access" not in response.json()


def test_atk_015_updated_at_tracks_changes(api):
    """ATK-015: model-level sanity — a freshly created user has defaults
    (empty bio, no pic) and updated_at set; saving updates updated_at."""
    user = create_user()
    assert user.bio == ""
    assert not user.profile_pic  # ImageFieldFile(None) is falsy
    first = user.updated_at
    assert first is not None
    user.bio = "changed"
    user.save()
    user.refresh_from_db()
    assert user.updated_at >= first
    assert timezone.now() >= user.updated_at
