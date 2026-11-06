"""Model tests for the accounts domain, named after the spec scenarios."""

import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import (
    EMAIL_TAKEN_ERROR,
    USERNAME_FORMAT_ERROR,
    USERNAME_LENGTH_ERROR,
    USERNAME_TAKEN_ERROR,
    User,
)

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def test_user_account_persisted():
    """Scenario: User account persisted — valid data is stored with UUID id,
    unique username/email, optional bio/profile_pic and a hashed password."""
    user = make_user(bio="hello world")

    # UUID identifier
    assert isinstance(user.id, uuid.UUID)
    assert user.pk == user.id

    # Optional bio and profile picture
    assert user.bio == "hello world"
    assert not user.profile_pic

    # Hashed (never plain-text) password
    assert user.password != RAW_PASSWORD
    assert user.check_password(RAW_PASSWORD)

    # Persisted and retrievable
    stored = User.objects.get(username="alice")
    assert stored.email == "alice@example.com"
    assert stored.check_password(RAW_PASSWORD)
    assert stored.updated_at is not None


def test_username_format_validation():
    """Scenario: Username format validation — usernames shorter than 3
    characters, longer than 150 characters or with non-alphanumeric
    characters are rejected with the spec error messages."""
    too_short = "ab"
    assert User.validate_registration(username=too_short, email="a@example.com") == (
        USERNAME_LENGTH_ERROR
    )

    too_long = "a" * 151
    assert User.validate_registration(username=too_long, email="a@example.com") == (
        USERNAME_LENGTH_ERROR
    )

    non_alphanumeric = "alice_1"
    assert (
        User.validate_registration(username=non_alphanumeric, email="a@example.com")
        == USERNAME_FORMAT_ERROR
    )

    # Boundary values are valid when the identity is free
    assert User.validate_registration(username="abc", email="a@example.com") is None
    assert User.validate_registration(username="a" * 150, email="a@example.com") is None
    assert User.validate_registration(username="Alice1", email="a@example.com") is None


def test_username_and_email_must_be_unique():
    """Field constraints from the data requirement: duplicate username and
    duplicate email are rejected at the database level."""
    make_user()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_user()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_user(email="other@example.com")


def test_validate_registration_reports_taken_identity():
    """Identity-duplicate rules: explicit spec messages for taken username
    and already registered email."""
    make_user()

    assert (
        User.validate_registration(username="alice", email="new@example.com")
        == USERNAME_TAKEN_ERROR
    )
    assert (
        User.validate_registration(username="newname", email="alice@example.com")
        == EMAIL_TAKEN_ERROR
    )
