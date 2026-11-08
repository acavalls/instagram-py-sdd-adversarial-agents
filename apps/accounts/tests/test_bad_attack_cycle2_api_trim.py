"""Cycle 2 attack: trim_whitespace=False fallout on the API (BUG-003 fix).

The spec only mandates >= 8 chars and byte-exact comparison/storage, so an
all-spaces 8-char password is valid and must work end-to-end. A username
with surrounding spaces violates the username rule as submitted; the API
CharField trims it — this test documents the trimming behavior.
"""

import pytest

pytestmark = pytest.mark.django_db

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"


class TestApiSpacedPassword:
    def test_register_and_login_with_8_space_password(self, client):
        response = client.post(
            REGISTER,
            {"username": "validuser", "email": "x@example.com", "password": "        "},
            content_type="application/json",
        )
        assert response.status_code == 201
        login = client.post(
            LOGIN,
            {"username": "validuser", "password": "        "},
            content_type="application/json",
        )
        assert login.status_code == 200
        assert "access" in login.json()

    def test_login_with_7_spaces_is_rejected(self, client):
        client.post(
            REGISTER,
            {"username": "validuser", "email": "x@example.com", "password": "        "},
            content_type="application/json",
        )
        login = client.post(
            LOGIN,
            {"username": "validuser", "password": "       "},
            content_type="application/json",
        )
        assert login.status_code == 401


class TestApiUsernameTrimConsistency:
    def test_api_register_trims_surrounding_spaces_from_username(self, client):
        response = client.post(
            REGISTER,
            {"username": "  validuser  ", "email": "x@example.com", "password": "password123"},
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["username"] == "validuser"
