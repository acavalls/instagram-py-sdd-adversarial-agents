"""Cycle 7 Bad attacks against change 2026-11-08-07-resolve-cycle6-findings.

Targets the three declared leniencies in the user-accounts delta:
  1. API registration email trim (declared inert, byte-exact storage).
  2. API login username trim (declared inert; password must stay
     byte-exact — never trimmed).
  3. API session-cookie fallback (expired/foreign sessions, CSRF on
     unsafe methods, JWT+session precedence).

Plus regression sanity: plain JWT login and 409 conflict mapping.
"""

from datetime import UTC

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
POSTS = "/api/posts/"


def _register(client, username="alice", email=None, password="password123"):
    if email is None:
        email = f"{username}@example.com"
    return client.post(
        REGISTER,
        {"username": username, "email": email, "password": password},
        format="json",
    )


def _login(client, username, password):
    return client.post(LOGIN, {"username": username, "password": password}, format="json")


class TestEmailTrimHostileInputs:
    def test_register_email_whose_trimmed_form_collides_returns_409(self, client):
        first = _register(client, "alice", "alice@example.com")
        assert first.status_code == 201

        padded = _register(client, "bob", "  alice@example.com  ")

        assert padded.status_code == 409
        assert padded.json() == {"error": "Email already registered"}
        assert client.get("/api/posts/").status_code in (401, 403)

    def test_register_whitespace_only_email_is_400_not_500(self, client):
        response = _register(client, "alice", "   ")

        assert response.status_code == 400
        assert "email" in response.json()

    def test_register_email_with_internal_tab_is_rejected_not_trimmed(self, client):
        response = _register(client, "alice", "a\tb@example.com")

        # Internal whitespace is NOT surrounding: the email must never be
        # accepted-and-stored with the tab intact, nor silently trimmed.
        assert response.status_code == 400

    def test_register_email_with_nbsp_padding_is_trimmed_to_byte_exact(self, client):
        response = _register(client, "alice", "\u00a0nbsp@example.com\u00a0")

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "nbsp@example.com"
        duplicate = _register(client, "bob", "nbsp@example.com")
        assert duplicate.status_code == 409


class TestLoginTrimBoundaries:
    def test_login_password_with_surrounding_spaces_is_not_trimmed(self, client):
        _register(client)
        plain = _login(client, "alice", "password123")
        assert plain.status_code == 200  # sanity inside the same run

        padded = _login(client, "alice", " password123 ")

        assert padded.status_code == 401
        assert padded.json() == {"error": "Invalid credentials"}

    def test_login_whitespace_only_username_is_401(self, client):
        _register(client)

        response = _login(client, "   ", "password123")

        assert response.status_code == 401
        assert response.json() == {"error": "Invalid credentials"}

    def test_login_nbsp_and_tab_padded_username_is_trimmed(self, client):
        _register(client)

        for padded in ("\u00a0alice\u00a0", "\talice\t", " \u2003alice "):
            response = _login(client, padded, "password123")
            assert response.status_code == 200, repr(padded)


class TestSessionFallbackAttacks:
    def _session_client(self, username: str = "alice") -> APIClient:
        client = APIClient()
        _register(client, username)
        from apps.accounts.models import User

        client.force_login(User.objects.get(username=username))
        return client

    def test_expired_session_cookie_is_rejected(self):
        client = self._session_client()
        from datetime import datetime, timedelta

        from django.contrib.sessions.models import Session

        session = Session.objects.get(session_key=client.cookies["sessionid"].value)
        session.expire_date = datetime.now(UTC) - timedelta(hours=1)
        session.save()

        response = client.get(POSTS)

        assert response.status_code in (401, 403)

    def test_session_cookie_after_logout_is_rejected(self):
        client = self._session_client()
        stale_cookie = client.cookies["sessionid"].value
        client.logout()

        client.cookies["sessionid"] = stale_cookie
        response = client.get(POSTS)

        assert response.status_code in (401, 403)

    def test_session_post_without_csrf_token_is_403(self):
        client = APIClient(enforce_csrf_checks=True)
        _register(client)
        from apps.accounts.models import User

        client.force_login(User.objects.get(username="alice"))

        response = client.post(POSTS, {"caption": "no csrf"}, format="json")

        # SessionAuthentication must enforce CSRF on unsafe methods.
        assert response.status_code == 403

    def test_jwt_of_other_user_does_not_override_session_identity(self):
        session_client = self._session_client("alice")
        other = APIClient()
        _register(other, "bob")
        bob_tokens = _login(other, "bob", "password123").json()

        response = session_client.post(
            POSTS,
            {"caption": "whose post?"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {bob_tokens['access']}",
        )

        assert response.status_code == 201
        assert response.json()["owner_username"] == "alice"

        response = session_client.post(
            POSTS,
            {"caption": "whose post?"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {bob_tokens['access']}",
        )

        assert response.status_code == 201
        assert response.json()["owner_username"] == "alice"


class TestRegressionSanity:
    def test_plain_jwt_login_and_conflict_mapping(self, client):
        _register(client)

        ok = _login(client, "alice", "password123")
        assert ok.status_code == 200
        assert ok.json()["access"]

        dup_username = _register(client, "alice", "other@example.com")
        assert dup_username.status_code == 409
        assert dup_username.json() == {"error": "Username already taken"}

        dup_email = _register(client, "bob", "alice@example.com")
        assert dup_email.status_code == 409
        assert dup_email.json() == {"error": "Email already registered"}
