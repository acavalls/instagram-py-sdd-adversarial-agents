import pytest
from django.contrib import messages

from apps.accounts.models import User

REGISTER_URL = "/web/register/"


def _stored_messages(response) -> list[str]:
    return [str(message) for message in messages.get_messages(response.wsgi_request)]


def _register(client, username: str, email: str, password: str = "password123"):
    return client.post(REGISTER_URL, {"username": username, "email": email, "password": password})


@pytest.mark.django_db
class TestWebRegisterView:
    def test_register_page_renders_form(self, client) -> None:
        response = client.get(REGISTER_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'name="username"' in html
        assert 'name="email"' in html
        assert 'name="password"' in html
        assert 'action="/web/register/"' in html

    def test_register_page_renders_auth_layout(self, client) -> None:
        response = client.get(REGISTER_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="auth-logo"' in html
        assert "bi bi-instagram" in html
        assert 'class="auth-card auth-card-secondary"' in html
        assert 'href="/web/login/"' in html
        assert "auth-footer" in html

    def test_successful_registration(self, client) -> None:
        response = _register(client, "alice", "alice@example.com")

        assert response.status_code == 302
        assert response["Location"] == "/web/login/"
        assert "Account created successfully. Please login." in _stored_messages(response)
        assert User.objects.filter(username="alice").exists()

    def test_duplicate_email_rejected(self, client) -> None:
        _register(client, "alice", "alice@example.com")

        response = _register(client, "bob", "alice@example.com")

        assert response.status_code == 200
        assert "Email already registered" in response.content.decode()
        assert User.objects.count() == 1

    def test_duplicate_username_rejected(self, client) -> None:
        _register(client, "alice", "alice@example.com")

        response = _register(client, "alice", "bob@example.com")

        assert response.status_code == 200
        assert "Username already taken" in response.content.decode()
        assert User.objects.count() == 1

    def test_password_too_short_rejected(self, client) -> None:
        response = _register(client, "alice", "alice@example.com", password="short")

        assert response.status_code == 200
        assert "Password must be at least 8 characters" in response.content.decode()
        assert not User.objects.exists()

    def test_username_format_validation(self, client) -> None:
        response = _register(client, "ab!", "alice@example.com")

        assert response.status_code == 200
        assert "Username must contain only letters and numbers" in response.content.decode()

        response = _register(client, "ab", "alice@example.com")

        assert response.status_code == 200
        assert "Username must be at least 3 characters" in response.content.decode()
        assert not User.objects.exists()

    def test_invalid_email_rejected(self, client) -> None:
        response = _register(client, "alice", "not-an-email")

        assert response.status_code == 200
        assert "Enter a valid email address." in response.content.decode()
        assert not User.objects.exists()

    def test_error_rerender_keeps_submitted_values(self, client) -> None:
        response = _register(client, "alice", "alice@example.com", password="short")

        html = response.content.decode()
        assert 'value="alice"' in html
        assert 'value="alice@example.com"' in html
