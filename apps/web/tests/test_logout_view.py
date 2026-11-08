import pytest
from django.contrib import messages

LOGIN_URL = "/web/login/"
LOGOUT_URL = "/web/logout/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"


def _stored_messages(response) -> list[str]:
    return [str(message) for message in messages.get_messages(response.wsgi_request)]


def _login(client, username: str = "alice", password: str = "password123"):
    return client.post(LOGIN_URL, {"username": username, "password": password})


@pytest.mark.django_db
class TestWebLogoutView:
    def test_successful_logout(self, client) -> None:
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
        )
        _login(client)
        assert client.session.get("_auth_user_id")

        response = client.post(LOGOUT_URL)

        assert response.status_code == 302
        assert response["Location"] == LOGIN_URL
        assert "You have been logged out" in _stored_messages(response)
        assert not client.session.get("_auth_user_id")
        assert client.get(FEED_URL).status_code == 302

    def test_protected_pages_require_login(self, client) -> None:
        response = client.get(FEED_URL)

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)

    def test_logout_is_post_only(self, client) -> None:
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
        )
        _login(client)

        response = client.get(LOGOUT_URL)

        assert response.status_code == 405
        assert client.session.get("_auth_user_id")
        assert client.get(FEED_URL).status_code == 200
