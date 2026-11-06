"""Adversarial web-UI attacks (The Bad) against the accounts capability.

Each test documents an attack (ATK-00N) targeting the register/login/logout
views, the session handling and the template rendering of user input.
"""

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/web/register/"
LOGIN_URL = "/web/login/"
LOGOUT_URL = "/web/logout/"
FEED_URL = "/web/feed/"

VALID = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "sup3r-secret-pw",
}


def post_register(client, **overrides):
    data = dict(VALID)
    data.update(overrides)
    return client.post(REGISTER_URL, data)


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


def create_user(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return User.objects.create_user(**data)


# --- Registration attacks --------------------------------------------------


def test_atk_016_register_all_fields_empty(client):
    """ATK-016: submit the register form with everything empty — must show an
    error toast, render 200 and create no user."""
    response = client.post(REGISTER_URL, {"username": "", "email": "", "password": ""})
    assert response.status_code == 200
    assert shown_messages(response), "an empty submission must show an error toast"
    assert not User.objects.exists()


def test_atk_017_register_whitespace_only_username(client):
    """ATK-017: username made only of whitespace is stripped to '' — must hit
    the length error, not crash or create a user."""
    response = post_register(client, username="   ")
    assert response.status_code == 200
    assert "Username must be between 3 and 150 characters" in shown_messages(response)
    assert not User.objects.exists()


def test_atk_018_register_long_and_unicode_username(client):
    """ATK-018: 151-char and unicode usernames rejected with a toast, no user
    created and no 500."""
    long_response = post_register(client, username="a" * 151)
    assert long_response.status_code == 200
    assert not User.objects.filter(username="a" * 151).exists()

    uni_response = post_register(client, username="álice")
    assert uni_response.status_code == 200
    assert "Username must contain only letters and numbers" in shown_messages(uni_response)


def test_atk_019_register_password_exactly_8_chars(client):
    """ATK-019: boundary password of exactly 8 chars must be accepted on the
    web flow with the success redirect and toast."""
    response = post_register(client, password="12345678")
    assert response.status_code == 302
    assert response.url == LOGIN_URL
    user = User.objects.get(username=VALID["username"])
    assert user.check_password("12345678")
    assert "Account created successfully. Please login." in shown_messages(response)


def test_atk_020_register_double_submit_same_session(client):
    """ATK-020: register twice in one session — the second attempt must fail
    with the exact duplicate messages, and only one row exists."""
    first = post_register(client)
    assert first.status_code == 302

    same_email = post_register(client, username="alice2")
    assert same_email.status_code == 200
    assert "Email already registered" in shown_messages(same_email)

    same_username = post_register(client, email="other@example.com")
    assert same_username.status_code == 200
    assert "Username already taken" in shown_messages(same_username)
    assert User.objects.filter(email=VALID["email"]).count() == 1


def test_atk_021_register_form_rerender_preserves_input(client):
    """ATK-021: a failed registration re-renders the form with the submitted
    username and email so the visitor can correct them."""
    response = post_register(client, username="bad name!", email="x@example.com")
    content = response.content.decode()
    assert 'value="bad name!"' in content
    assert 'value="x@example.com"' in content
    # The password must NOT be echoed back into the page.
    assert VALID["password"] not in content


def test_atk_022_web_registration_stores_hashed_password(client):
    """ATK-022: whatever path the account is created through, the stored
    password is a hash, never the plaintext."""
    post_register(client)
    user = User.objects.get(username=VALID["username"])
    assert user.password != VALID["password"]
    assert user.check_password(VALID["password"])
    assert VALID["password"] not in user.password


# --- Session / login / logout attacks --------------------------------------


def test_atk_023_login_failure_generic_and_identical(client):
    """ATK-023: wrong password and unknown username produce the identical
    generic 'Invalid credentials' error — the cause is never revealed."""
    create_user()
    wrong_password = client.post(
        LOGIN_URL, {"username": VALID["username"], "password": "wrong-password"}
    )
    unknown_user = client.post(LOGIN_URL, {"username": "ghost", "password": "wrong-password"})

    assert wrong_password.status_code == 200
    assert unknown_user.status_code == 200
    assert shown_messages(wrong_password) == shown_messages(unknown_user)
    assert shown_messages(wrong_password) == ["Invalid credentials"]
    assert not User.objects.filter(username="ghost").exists()


def test_atk_024_logout_twice_then_login_again(client):
    """ATK-024: hostile sequence — logout twice (second on an already-logged-
    out session must not crash), then login again works."""
    create_user()
    client.post(LOGIN_URL, {"username": VALID["username"], "password": VALID["password"]})
    first = client.post(LOGOUT_URL)
    assert first.status_code == 302
    assert first.url == LOGIN_URL
    assert "You have been logged out" in shown_messages(first)

    second = client.post(LOGOUT_URL)
    assert second.status_code == 302  # no crash on a dead session

    again = client.post(LOGIN_URL, {"username": VALID["username"], "password": VALID["password"]})
    assert again.status_code == 302
    assert again.url == FEED_URL
    assert "Logged in successfully" in shown_messages(again)


def test_atk_025_feed_with_garbage_session_cookie(client):
    """ATK-025: a corrupted session cookie must not crash the protected page —
    the user is treated as anonymous and redirected to login."""
    client.cookies["sessionid"] = "totally-garbage-value!@#$"
    response = client.get(FEED_URL)
    assert response.status_code == 302
    assert response.url.startswith(LOGIN_URL)


def test_atk_026_feed_requires_login(client):
    """ATK-026: anonymous access to the protected page redirects to login;
    a logged-in session gets a 200."""
    anonymous = client.get(FEED_URL)
    assert anonymous.status_code == 302
    assert anonymous.url.startswith(LOGIN_URL)

    create_user()
    client.post(LOGIN_URL, {"username": VALID["username"], "password": VALID["password"]})
    authenticated = client.get(FEED_URL)
    assert authenticated.status_code == 200


def test_atk_027_xss_in_login_rerender(client):
    """ATK-027: inject markup through the login form username — the template
    must escape it, never render a raw <script> tag."""
    payload = "<script>alert(1)</script>"
    response = client.post(LOGIN_URL, {"username": payload, "password": "whatever123"})
    content = response.content.decode()
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content  # auto-escaped


def test_atk_028_xss_in_register_email_rerender(client):
    """ATK-028: inject markup through the register email field — must be
    escaped on the error re-render."""
    payload = '"><script>alert(1)</script>'
    response = post_register(client, email=payload)
    content = response.content.decode()
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in content


def test_atk_029_login_strips_whitespace_username(client):
    """ATK-029: login with a whitespace-padded username (web strips input) —
    must still authenticate the same user, not fail mysteriously."""
    create_user()
    response = client.post(
        LOGIN_URL, {"username": f"  {VALID['username']}  ", "password": VALID["password"]}
    )
    assert response.status_code == 302
    assert response.url == FEED_URL
