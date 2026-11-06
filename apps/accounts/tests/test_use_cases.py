"""Use case tests for registration and authentication (tasks 3.1 and 4.1)."""

import pytest

from apps.accounts.models import EMAIL_TAKEN_ERROR, USERNAME_TAKEN_ERROR, User
from apps.accounts.use_cases import (
    INVALID_CREDENTIALS_ERROR,
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


def make_use_case() -> RegisterUserUseCase:
    return RegisterUserUseCase()


def test_register_user_success():
    output = make_use_case().execute(
        RegisterUserInput(username="alice", email="alice@example.com", password=RAW_PASSWORD)
    )
    assert output.success is True
    assert output.error is None
    assert output.user is not None
    assert output.user.username == "alice"
    # The password is hashed by the service, never stored in plain text.
    assert output.user.password != RAW_PASSWORD
    assert output.user.check_password(RAW_PASSWORD)
    assert User.objects.filter(username="alice").exists()


def test_register_user_duplicate_email_rejected():
    make_use_case().execute(
        RegisterUserInput(username="bob", email="alice@example.com", password=RAW_PASSWORD)
    )
    output = make_use_case().execute(
        RegisterUserInput(username="alice", email="alice@example.com", password=RAW_PASSWORD)
    )
    assert output.success is False
    assert output.error == EMAIL_TAKEN_ERROR
    assert output.user is None
    assert not User.objects.filter(username="alice").exists()


def test_register_user_duplicate_username_rejected():
    make_use_case().execute(
        RegisterUserInput(username="alice", email="bob@example.com", password=RAW_PASSWORD)
    )
    output = make_use_case().execute(
        RegisterUserInput(username="alice", email="alice@example.com", password=RAW_PASSWORD)
    )
    assert output.success is False
    assert output.error == USERNAME_TAKEN_ERROR
    assert output.user is None
    assert not User.objects.filter(email="alice@example.com").exists()


def test_register_user_invalid_username_format_rejected():
    """The use case surfaces the username format rules of the model."""
    output = make_use_case().execute(
        RegisterUserInput(username="alice_1", email="alice@example.com", password=RAW_PASSWORD)
    )
    assert output.success is False
    assert output.error == "Username must contain only letters and numbers"
    assert output.user is None


def make_auth_use_case() -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase()


def test_authenticate_user_success():
    make_use_case().execute(
        RegisterUserInput(username="alice", email="alice@example.com", password=RAW_PASSWORD)
    )
    output = make_auth_use_case().execute(
        AuthenticateUserInput(username="alice", password=RAW_PASSWORD)
    )
    assert output.success is True
    assert output.error is None
    assert output.user is not None
    assert output.user.username == "alice"


def test_authenticate_user_wrong_password_generic_error():
    make_use_case().execute(
        RegisterUserInput(username="alice", email="alice@example.com", password=RAW_PASSWORD)
    )
    output = make_auth_use_case().execute(
        AuthenticateUserInput(username="alice", password="not-the-password")
    )
    assert output.success is False
    assert output.error == INVALID_CREDENTIALS_ERROR == "Invalid credentials"
    assert output.user is None


def test_authenticate_user_unknown_username_same_generic_error():
    """An unknown username yields the identical generic error as a wrong
    password: the cause is never revealed."""
    output = make_auth_use_case().execute(
        AuthenticateUserInput(username="ghost", password="whatever-password")
    )
    assert output.success is False
    assert output.error == INVALID_CREDENTIALS_ERROR
    assert output.user is None
