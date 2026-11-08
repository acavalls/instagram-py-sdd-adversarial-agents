import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import (
    ERROR_STORY_EXPIRY_MISMATCH,
    STORY_LIFETIME,
    Story,
    StoryView,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_story(owner: User) -> Story:
    story = Story(owner=owner)
    story.image.save("story.png", ContentFile(b"data"), save=False)
    story.save()
    return story


class TestStoryPersistedWithPlaceholderMedia:
    @pytest.mark.django_db
    def test_story_persisted_with_placeholder_media(self) -> None:
        user = _make_user()
        before = timezone.now()

        story = _make_story(user)

        stored = Story.objects.get(pk=story.pk)
        after = timezone.now()
        assert isinstance(stored.id, uuid.UUID)
        assert stored.owner == user
        assert stored.media_type == Story.MediaType.IMAGE
        created_local = timezone.localtime(stored.created_at)
        assert stored.image.name.startswith(
            f"stories/{created_local:%Y}/{created_local:%m}/{created_local:%d}/"
        )
        assert before <= stored.created_at <= after
        assert stored.expires_at == stored.created_at + STORY_LIFETIME
        assert stored.expires_at == stored.created_at + timedelta(hours=24)

    @pytest.mark.django_db
    def test_explicit_matching_expiry_is_accepted(self) -> None:
        user = _make_user()
        story = Story(owner=user)
        story.image.save("story.png", ContentFile(b"data"), save=False)
        story.expires_at = story.created_at + STORY_LIFETIME

        story.save()

        stored = Story.objects.get(pk=story.pk)
        assert stored.expires_at == stored.created_at + timedelta(hours=24)


class TestMismatchingExplicitExpiryRejected:
    @pytest.mark.django_db
    @pytest.mark.parametrize("offset", [timedelta(hours=23), timedelta(hours=25)])
    def test_mismatching_explicit_expiry_rejected(self, offset: timedelta) -> None:
        user = _make_user()
        story = Story(owner=user, expires_at=timezone.now() + offset)
        story.image.save("story.png", ContentFile(b"data"), save=False)

        with pytest.raises(ValidationError, match=ERROR_STORY_EXPIRY_MISMATCH):
            story.save()

        assert not Story.objects.exists()


class TestExpiredStoryIsNotActive:
    @pytest.mark.django_db
    def test_expired_story_is_not_active(self) -> None:
        user = _make_user()
        story = _make_story(user)
        assert story in list(Story.objects.filter(owner=user).active())
        assert story in list(Story.objects.active())

        Story.objects.filter(pk=story.pk).update(expires_at=timezone.now() - timedelta(hours=1))

        expired = Story.objects.get(pk=story.pk)
        assert expired.expires_at < timezone.now()
        assert list(Story.objects.active()) == []
        assert list(Story.objects.filter(owner=user).active()) == []


class TestBulkPathsBypassSavePathExpiryInvariant:
    """The 24-hour invariant is scoped to the save path: the raw queryset
    writes (update(), bulk_create) store whatever expiry values they are
    given (stories: "Story data model" — "Bulk paths bypass the save-path
    expiry invariant")."""

    @pytest.mark.django_db
    def test_bulk_paths_bypass_the_save_path_expiry_invariant(self) -> None:
        user = _make_user()
        now = timezone.now()

        queryset_update = _make_story(user)
        Story.objects.filter(pk=queryset_update.pk).update(expires_at=now + timedelta(days=30))
        updated = Story.objects.get(pk=queryset_update.pk)
        assert updated.expires_at == now + timedelta(days=30)

        bulk_created = Story(
            owner=user,
            created_at=now,
            expires_at=now + timedelta(days=365),
        )
        Story.objects.bulk_create([bulk_created])
        smuggled = Story.objects.get(pk=bulk_created.pk)
        assert smuggled.expires_at - smuggled.created_at == timedelta(days=365)


class TestStoryViewUniquePair:
    @pytest.mark.django_db
    def test_story_view_unique_pair_rejected(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        story = _make_story(owner)
        StoryView.objects.create(story=story, viewer=viewer)

        with pytest.raises(IntegrityError), transaction.atomic():
            StoryView.objects.create(story=story, viewer=viewer)

        assert StoryView.objects.count() == 1
        assert StoryView.objects.get(story=story, viewer=viewer).viewed_at is not None
