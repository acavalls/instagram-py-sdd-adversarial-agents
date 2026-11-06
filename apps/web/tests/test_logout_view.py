"""Web logout and protected-page tests, named after the spec scenarios (task 4.2)."""

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = "/web/login/"
LOGOUT_URL = "/web/logout/"
FEED_URL = "/web/feed/"


@pytest.fixture
def alice():
    return User.objects.create_user(
        username="alice", email="alice@example.com", password="sup3r-secret-pw"
    )


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


def test_successful_logout(client, alice):
    client.force_login(alice)
    assert "_auth_user_id" in client.session

    response = client.post(LOGOUT_URL)

    assert response.status_code == 302
    assert response.url == LOGIN_URL
    assert "You have been logged out" in shown_messages(response)
    # The session was cleared: the user is no longer authenticated.
    assert "_auth_user_id" not in client.session
    # After logout the protected feed redirects to the login page again
    # (login_required may add its standard ?next= parameter).
    follow_up = client.get(FEED_URL)
    assert follow_up.status_code == 302
    assert follow_up.url.startswith(LOGIN_URL)


def test_get_logout_no_longer_logs_out(client, alice):
    """Logout is POST-only (Django's CSRF recommendation): a GET request must
    answer 405 without touching the session, so a pre-fetched/logout-via-link
    GET cannot end the user's session."""
    client.force_login(alice)
    assert "_auth_user_id" in client.session

    response = client.get(LOGOUT_URL)

    assert response.status_code == 405
    # The session survived: the user is still authenticated.
    assert "_auth_user_id" in client.session
    assert client.get(FEED_URL).status_code == 200


def test_protected_pages_require_login(client):
    """An anonymous visitor requesting the (login-required) feed page is
    redirected to the login page (the ?next= parameter is Django's standard
    login_required behavior, pointing back at the protected page)."""
    response = client.get(FEED_URL)

    assert response.status_code == 302
    assert response.url.startswith(LOGIN_URL)
    assert "next=/web/feed/" in response.url


def test_authenticated_user_reaches_protected_feed(client, alice):
    """The same page is reachable once the session exists (login_required
    redirects only anonymous visitors)."""
    client.force_login(alice)

    response = client.get(FEED_URL)

    assert response.status_code == 200
