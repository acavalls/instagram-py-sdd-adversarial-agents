import uuid

import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.social.models import Follow


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


class TestFollowPersisted:
    @pytest.mark.django_db
    def test_follow_persisted(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")

        follow = Follow.objects.create(follower=follower, following=following)

        assert isinstance(follow.id, uuid.UUID)
        assert follow.created_at is not None
        stored = Follow.objects.get(pk=follow.pk)
        assert stored.follower == follower
        assert stored.following == following


class TestSelfFollowRejectedAtTheDatabaseLevel:
    @pytest.mark.django_db
    def test_self_follow_rejected_at_the_database_level(self) -> None:
        user = _make_user("alice")

        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=user, following=user)


class TestDuplicateFollowRejectedAtTheDatabaseLevel:
    @pytest.mark.django_db
    def test_duplicate_follow_rejected_at_the_database_level(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")
        Follow.objects.create(follower=follower, following=following)

        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=follower, following=following)
