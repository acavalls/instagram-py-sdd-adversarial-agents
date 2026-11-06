"""Web login view tests, named after the spec scenarios (tasks 4.1 and 4.3)."""

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"

CREDENTIALS = {"username": "alice", "password": "sup3r-secret-pw"}


@pytest.fixture
def alice():
    return User.objects.create_user(email="alice@example.com", **CREDENTIALS)


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


def test_login_page_renders_form(client):
    """The login page renders in the Instagram card style with the expected
    form fields and the link to the registration page (template test)."""
    response = client.get(LOGIN_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="username"' in content
    assert 'name="password"' in content
    assert "Log in" in content
    assert REGISTER_URL in content


def test_successful_web_login(client, alice):
    response = client.post(LOGIN_URL, CREDENTIALS)

    assert response.status_code == 302
    assert response.url == FEED_URL
    assert "Logged in successfully" in shown_messages(response)
    # A session was created: the now-authenticated user reaches the feed.
    assert "_auth_user_id" in client.session
    assert client.get(FEED_URL).status_code == 200


def test_failed_web_login_hides_the_cause(client, alice):
    """A wrong password re-renders the login page with the single generic
    error, never revealing which field was wrong."""
    response = client.post(LOGIN_URL, {"username": "alice", "password": "wrong-password"})

    assert response.status_code == 200
    assert shown_messages(response) == ["Invalid credentials"]
    content = response.content.decode()
    assert "Invalid credentials" in content
    # The submitted username is echoed back for correction, but no hint about
    # the failing field is rendered.
    assert 'value="alice"' in content
    assert "password was wrong" not in content
    assert "unknown" not in content.lower()


def test_failed_web_login_unknown_username_same_generic_error(client, alice):
    """An unknown username yields the exact same generic error as a wrong
    password, proving the cause is hidden (spec: Failed web login hides the
    cause)."""
    wrong_password = client.post(LOGIN_URL, {"username": "alice", "password": "wrong"})
    unknown_username = client.post(LOGIN_URL, {"username": "ghost", "password": "wrong"})

    assert wrong_password.status_code == 200
    assert unknown_username.status_code == 200
    assert shown_messages(wrong_password) == ["Invalid credentials"]
    assert shown_messages(unknown_username) == ["Invalid credentials"]
    assert not User.objects.filter(username="ghost").exists()
