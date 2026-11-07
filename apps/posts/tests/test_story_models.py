"""Model tests for the stories capability, named after the spec scenarios."""

import io
import uuid
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.posts.models import STORY_EXPIRY_HOURS, Story, StoryView

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "sup3r-secret-pw",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_placeholder_jpeg(color=(120, 40, 200)) -> bytes:
    """Deterministic placeholder JPEG bytes (no copyrighted assets)."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_story(user, **overrides):
    """Create a story through the model creation path with a real image file
    so the dated ``upload_to`` path is exercised."""
    data = {"owner": user}
    data.update(overrides)
    story = Story(**data)
    story.image.save(
        "story.jpg",
        ContentFile(make_placeholder_jpeg()),
        save=False,
    )
    story.save()
    return story


def test_story_persisted_with_placeholder_media(tmp_path, settings):
    """Scenario: Story persisted with placeholder media — a story created for
    a user is stored with an image file under the dated stories path, a
    creation timestamp, and an expiration timestamp exactly 24 hours later."""
    settings.MEDIA_ROOT = tmp_path
    user = make_user()

    story = make_story(user)

    # UUID identifier and persisted row
    assert isinstance(story.pk, uuid.UUID)
    stored = Story.objects.get(pk=story.pk)
    assert stored.owner == user
    assert list(user.stories.all()) == [story]

    # Image stored under the dated stories path
    image_name = stored.image.name
    assert image_name is not None
    assert image_name.startswith("stories/")
    year, month, day = stored.created_at.strftime("%Y/%m/%d").split("/")
    assert image_name.startswith(f"stories/{year}/{month}/{day}/")
    assert image_name.endswith(".jpg")
    assert (tmp_path / image_name).exists()

    # Media defaults to image (the only kind the creation flow produces)
    assert stored.media_type == "image"

    # Creation timestamp is set; expiration is exactly created_at + 24h
    assert stored.created_at is not None
    assert stored.expires_at == stored.created_at + timedelta(hours=STORY_EXPIRY_HOURS)

    # Newest stories first in listings (Post ordering convention)
    newest = make_story(user)
    assert list(Story.objects.all()) == [newest, story]


def test_story_expiry_set_on_every_persistence_path():
    """The ``Story.save`` guard fills an empty ``expires_at`` on every
    persistence path (mirroring the Post.save guard pattern); an explicit
    ``expires_at`` is respected so the cleanup queries stay testable."""
    user = make_user()

    # A bare save() without expires_at is filled with created_at + 24h.
    bare = Story(owner=user)
    bare.image.save("bare.jpg", ContentFile(make_placeholder_jpeg()), save=False)
    bare.save()
    bare.refresh_from_db()
    assert bare.expires_at == bare.created_at + timedelta(hours=STORY_EXPIRY_HOURS)

    # An explicit expires_at is never overwritten by the guard.
    explicit_at = timezone.now() + timedelta(hours=1)
    explicit = Story(owner=user, expires_at=explicit_at)
    explicit.image.save("explicit.jpg", ContentFile(make_placeholder_jpeg()), save=False)
    explicit.save()
    explicit.refresh_from_db()
    assert explicit.expires_at == explicit_at


def test_story_view_unique_per_story_and_viewer():
    """A (story, viewer) pair is recorded at most once (spec: Story view
    tracking); the unique constraint backs the idempotent mark_viewed."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    story = make_story(owner)

    first = StoryView.objects.create(story=story, viewer=viewer)
    assert first.viewed_at is not None
    assert list(story.views.all()) == [first]
    assert list(viewer.story_views.all()) == [first]

    # The same pair cannot be recorded twice.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            StoryView.objects.create(story=story, viewer=viewer)

    # A different viewer on the same story is a separate record.
    other = make_user(username="carol", email="carol@example.com")
    second = StoryView.objects.create(story=story, viewer=other)
    assert StoryView.objects.filter(story=story).count() == 2
    assert set(story.views.all()) == {first, second}
