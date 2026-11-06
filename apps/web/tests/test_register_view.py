"""Web register view tests, named after the spec scenarios (task 3.2)."""

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/web/register/"
LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"

VALID_DATA = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "sup3r-secret-pw",
}


def post_register(client, **overrides):
    data = dict(VALID_DATA)
    data.update(overrides)
    return client.post(REGISTER_URL, data)


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


def test_register_page_renders_form(client):
    """The registration page renders in the Instagram card style with the
    expected form fields."""
    response = client.get(REGISTER_URL)
    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="username"' in content
    assert 'name="email"' in content
    assert 'name="password"' in content
    assert "Sign up" in content


def test_successful_registration(client):
    response = post_register(client)

    assert response.status_code == 302
    assert response.url == LOGIN_URL
    user = User.objects.get(username="alice")
    assert user.email == "alice@example.com"
    assert user.password != VALID_DATA["password"]
    assert user.check_password(VALID_DATA["password"])
    assert "Account created successfully. Please login." in shown_messages(response)


def test_duplicate_email_rejected(client):
    User.objects.create_user(username="bob", email="alice@example.com", password="password123")

    response = post_register(client)

    assert response.status_code == 200
    assert not User.objects.filter(username="alice").exists()
    assert "Email already registered" in shown_messages(response)


def test_duplicate_username_rejected(client):
    User.objects.create_user(username="alice", email="bob@example.com", password="password123")

    response = post_register(client)

    assert response.status_code == 200
    assert not User.objects.filter(email="alice@example.com").exists()
    assert "Username already taken" in shown_messages(response)


def test_web_register_rejects_malformed_email(client):
    """The web path enforces the email-shape rule with the same message as
    the API path (design decision 2: both validation locations, same rules)."""
    response = post_register(client, email="not-an-email")

    assert response.status_code == 200
    assert not User.objects.filter(username="alice").exists()
    assert "Enter a valid email address." in shown_messages(response)
    # Re-render keeps the submitted values for correction (except the
    # password, which is never echoed back).
    content = response.content.decode()
    assert 'value="not-an-email"' in content


def test_password_too_short_rejected(client):
    response = post_register(client, password="short")

    assert response.status_code == 200
    assert not User.objects.filter(username="alice").exists()
    assert "Password must be at least 8 characters" in shown_messages(response)


def test_username_format_validation(client):
    response = post_register(client, username="al!")
    assert response.status_code == 200
    assert not User.objects.filter(email="alice@example.com").exists()
    assert "Username must contain only letters and numbers" in shown_messages(response)

    response = post_register(client, username="ab")
    assert response.status_code == 200
    assert "Username must be between 3 and 150 characters" in shown_messages(response)


def test_padded_password_round_trips_web_register_and_login(client):
    """The web path never trims the password (DRIFT-012): a password
    registered with surrounding spaces is stored byte-exactly and only
    authenticates with those same spaces (parity with the API path)."""
    padded_password = " sup3r-secret-pw "

    register_response = post_register(client, password=padded_password)
    assert register_response.status_code == 302
    assert register_response.url == LOGIN_URL
    user = User.objects.get(username="alice")
    assert user.check_password(padded_password)

    login_response = client.post(LOGIN_URL, {"username": "alice", "password": padded_password})
    assert login_response.status_code == 302
    assert login_response.url == FEED_URL
    assert "Logged in successfully" in shown_messages(login_response)
