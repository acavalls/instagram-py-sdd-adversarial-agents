"""Service tests for user creation (task 3.1)."""

import pytest

from apps.accounts.models import EMAIL_TAKEN_ERROR, USERNAME_TAKEN_ERROR, User
from apps.accounts.services import UserService

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


def test_create_user_success():
    user, error = UserService().create_user(
        username="alice", email="alice@example.com", password=RAW_PASSWORD
    )
    assert error is None
    assert user is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    # The password is stored hashed, never in plain text.
    assert user.password != RAW_PASSWORD
    assert user.check_password(RAW_PASSWORD)
    assert User.objects.filter(username="alice").exists()


def test_create_user_duplicate_email_rejected():
    UserService().create_user(username="bob", email="alice@example.com", password=RAW_PASSWORD)
    user, error = UserService().create_user(
        username="alice", email="alice@example.com", password=RAW_PASSWORD
    )
    assert user is None
    assert error == EMAIL_TAKEN_ERROR
    assert not User.objects.filter(username="alice").exists()


def test_create_user_duplicate_username_rejected():
    UserService().create_user(username="alice", email="bob@example.com", password=RAW_PASSWORD)
    user, error = UserService().create_user(
        username="alice", email="alice@example.com", password=RAW_PASSWORD
    )
    assert user is None
    assert error == USERNAME_TAKEN_ERROR
    assert not User.objects.filter(email="alice@example.com").exists()
