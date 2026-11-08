"""Cycle 2 attack: messages partial fix surface (BUG-002) and trim fallout.

Covers: toast rendered exactly once on the feed after login, escaping of
messages content, the #messages mount, and byte-exact handling of
all-space passwords on the web path.
"""

import pytest

pytestmark = pytest.mark.django_db

REGISTER_URL = "/web/register/"
LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"


def _register(client, username="validuser", email="x@example.com", password="password123"):
    return client.post(
        REGISTER_URL,
        {"username": username, "email": email, "password": password},
    )


class TestToastRendering:
    def test_login_success_toast_renders_exactly_once_on_feed(self, client):
        _register(client)
        client.post(LOGIN_URL, {"username": "validuser", "password": "password123"})
        response = client.get(FEED_URL)
        assert response.status_code == 200
        body = response.content.decode()
        assert body.count("Logged in successfully") == 1
        assert body.count('id="messages"') == 1

    def test_logout_toast_renders_exactly_once_on_login_page(self, client):
        _register(client)
        client.post(LOGIN_URL, {"username": "validuser", "password": "password123"})
        client.post(LOGIN_URL.replace("/login/", "/logout/"))
        response = client.get(LOGIN_URL)
        body = response.content.decode()
        assert body.count("You have been logged out") == 1
        assert body.count('id="messages"') == 1


class TestTrimFalloutWebPath:
    def test_web_register_with_all_spaces_password_rejected_as_too_short_lookalike(self, client):
        # 8 spaces is 8 chars: it must NOT be trimmed, so it is accepted by
        # the length rule and stored byte-exactly (spec: >= 8, byte-exact).
        response = _register(client, password="        ")
        assert response.status_code == 302
        client.post(LOGIN_URL, {"username": "validuser", "password": "        "})
        assert client.get(FEED_URL).status_code == 200

    def test_web_login_rejects_trimmed_variant_of_spaced_password(self, client):
        _register(client, password="        ")
        client.post(LOGIN_URL, {"username": "validuser", "password": "password123"})
        # wrong byte-exact variant must not log in
        response = client.post(LOGIN_URL, {"username": "validuser", "password": "       "})
        assert b"Invalid credentials" in response.content

    def test_web_register_rejects_username_with_surrounding_spaces(self, client):
        response = _register(client, username=" validuser ")
        assert response.status_code == 200
        assert b"only letters and numbers" in response.content
