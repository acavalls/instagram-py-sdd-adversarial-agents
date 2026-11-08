import pytest
from django.contrib import messages

from apps.accounts.use_cases import ERROR_INVALID_CREDENTIALS

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"


def _stored_messages(response) -> list[str]:
    return [str(message) for message in messages.get_messages(response.wsgi_request)]


def _login(client, username: str, password: str):
    return client.post(LOGIN_URL, {"username": username, "password": password})


def _register(client, username: str, email: str, password: str = "password123"):
    return client.post(REGISTER_URL, {"username": username, "email": email, "password": password})


@pytest.mark.django_db
class TestWebLoginView:
    def test_login_page_renders_form(self, client) -> None:
        response = client.get(LOGIN_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'name="username"' in html
        assert 'name="password"' in html
        assert 'action="/web/login/"' in html
        assert "/web/register/" in html
        assert "auth-footer" in html
        assert 'data-testid="auth-logo"' in html
        assert "bi bi-instagram" in html

    def test_login_page_displays_error(self, client) -> None:
        response = _login(client, "alice", "wrong-password")

        assert response.status_code == 200
        html = response.content.decode()
        assert "form-errors" in html
        assert ERROR_INVALID_CREDENTIALS in html

    def test_successful_web_login(self, client) -> None:
        _register(client, "alice", "alice@example.com")

        response = _login(client, "alice", "password123")

        assert response.status_code == 302
        assert response["Location"] == FEED_URL
        assert "Logged in successfully" in _stored_messages(response)
        assert client.session.get("_auth_user_id")
        assert client.get(FEED_URL).status_code == 200

    def test_failed_web_login_hides_the_cause(self, client) -> None:
        _register(client, "alice", "alice@example.com")

        response = _login(client, "alice", "wrong-password")

        assert response.status_code == 200
        html = response.content.decode()
        assert ERROR_INVALID_CREDENTIALS in html
        assert not client.session.get("_auth_user_id")

        response = _login(client, "unknown-user", "password123")

        assert response.status_code == 200
        assert ERROR_INVALID_CREDENTIALS in response.content.decode()
        assert not client.session.get("_auth_user_id")

    def test_login_with_blank_fields_shows_generic_error(self, client) -> None:
        response = _login(client, "", "password123")

        assert response.status_code == 200
        assert ERROR_INVALID_CREDENTIALS in response.content.decode()
        assert not client.session.get("_auth_user_id")

        response = _login(client, "alice", "")

        assert response.status_code == 200
        assert ERROR_INVALID_CREDENTIALS in response.content.decode()

    def test_authenticated_user_getting_login_page_redirects_to_feed(self, client) -> None:
        _register(client, "alice", "alice@example.com")
        _login(client, "alice", "password123")

        response = client.get(LOGIN_URL)

        assert response.status_code == 302
        assert response["Location"] == FEED_URL

    def test_login_page_rerender_keeps_submitted_username(self, client) -> None:
        response = _login(client, "alice", "wrong-password")

        html = response.content.decode()
        assert 'value="alice"' in html
