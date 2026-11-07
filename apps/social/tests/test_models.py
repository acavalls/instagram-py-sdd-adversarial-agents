"""Model tests for the social domain, named after the spec scenarios."""

import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "sup3r-secret-pw",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def test_follow_persisted():
    """Scenario: Follow persisted — the relationship is stored with a UUID
    identifier and a creation timestamp, reachable through both related
    names."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")

    follow = Follow.objects.create(follower=alice, following=bob)

    assert isinstance(follow.id, uuid.UUID)
    assert follow.pk == follow.id
    assert follow.created_at is not None

    stored = Follow.objects.get(pk=follow.pk)
    assert stored.follower == alice
    assert stored.following == bob

    assert list(alice.following.all()) == [follow]
    assert list(bob.followers.all()) == [follow]


def test_self_follow_rejected():
    """Scenario: Self-follow rejected — the database rejects a relationship
    where the follower and the followed user are the same user."""
    alice = make_user()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Follow.objects.create(follower=alice, following=alice)

    assert not Follow.objects.exists()


def test_duplicate_follow_rejected():
    """Scenario: Duplicate follow rejected — the database rejects a second
    relationship for the same (follower, following) pair."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    Follow.objects.create(follower=alice, following=bob)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Follow.objects.create(follower=alice, following=bob)

    assert Follow.objects.count() == 1
