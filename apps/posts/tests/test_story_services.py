"""Service tests for the stories capability, named after the spec scenarios."""

import io
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.posts.models import STORY_EXPIRY_HOURS, Story, StoryView
from apps.posts.services import StoryService
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_media_root(tmp_path, settings):
    """Keep generated placeholder files inside a per-test media root."""
    settings.MEDIA_ROOT = tmp_path


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "sup3r-secret-pw",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_follow(follower: User, following: User) -> Follow:
    return Follow.objects.create(follower=follower, following=following)


def make_placeholder_jpeg(color=(120, 40, 200)) -> bytes:
    """Deterministic placeholder JPEG bytes (no copyrighted assets)."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_story(user, **overrides):
    """Create a story with a real image file; an explicit ``expires_at`` is
    respected by the model save-guard, which is what the expired-story tests
    rely on."""
    data = {"owner": user}
    data.update(overrides)
    story = Story(**data)
    story.image.save("story.jpg", ContentFile(make_placeholder_jpeg()), save=False)
    story.save()
    return story


def make_expired_story(user, **overrides):
    overrides.setdefault("expires_at", timezone.now() - timedelta(hours=1))
    return make_story(user, **overrides)


def test_story_service_create_generates_placeholder_jpeg(tmp_path):
    """The service creation path stores a generated placeholder JPEG with the
    24h expiration (spec: Story data model, creation side)."""
    user = make_user()

    story = StoryService().create(user)

    stored = Story.objects.get(pk=story.pk)
    assert stored.owner == user
    assert stored.image.name is not None
    assert stored.image.name.endswith(".jpg")
    assert stored.media_type == "image"
    assert stored.expires_at == stored.created_at + timedelta(hours=STORY_EXPIRY_HOURS)
    assert (tmp_path / stored.image.name).exists()


def test_expired_story_is_not_active():
    """Scenario: Expired story is not active — a story whose expiration has
    passed is not returned as an active story for its owner, not in any feed,
    and is removed by the cleanup."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    make_follow(follower=viewer, following=owner)
    expired = make_expired_story(owner)
    active = make_story(owner)
    service = StoryService()

    # Not active for its owner...
    assert expired not in service.get_active_for_user(owner)
    assert service.get_active_for_user(owner) == [active]

    # ...not in any feed (the owner's active story remains, the expired one
    # does not)...
    groups = service.get_feed_stories(viewer)
    assert [item.story for item in groups[0].stories] == [active]

    # ...and removed by the cleanup.
    assert service.cleanup_expired() == 1
    assert not Story.objects.filter(pk=expired.pk).exists()
    assert list(Story.objects.all()) == [active]


def test_bar_lists_followed_users_with_active_stories():
    """Scenario: Bar lists followed users with active stories — a followed
    user's active stories come back grouped under their owner, newest first."""
    viewer = make_user()
    followed = make_user(username="carol", email="carol@example.com")
    make_follow(follower=viewer, following=followed)
    older = make_story(followed)
    newer = make_story(followed)

    groups = StoryService().get_feed_stories(viewer)

    assert len(groups) == 1
    group = groups[0]
    assert group.owner == followed
    assert [item.story for item in group.stories] == [newer, older]
    # Nothing viewed yet: every story and the whole group are unviewed.
    assert all(not item.is_viewed for item in group.stories)
    assert group.is_viewed is False


def test_bar_excludes_non_followed_users():
    """Scenario: Bar excludes non-followed users — a user the viewer does not
    follow never appears in the feed stories, even with active stories."""
    viewer = make_user()
    stranger = make_user(username="dave", email="dave@example.com")
    make_story(stranger)

    assert StoryService().get_feed_stories(viewer) == []


def test_unviewed_groups_first():
    """Scenario: Unviewed groups first — the group whose newest story the
    viewer has not seen comes before the group whose newest story is viewed;
    within a group stories keep their newest-first creation order."""
    viewer = make_user()
    viewed_owner = make_user(username="carol", email="carol@example.com")
    unviewed_owner = make_user(username="erin", email="erin@example.com")
    make_follow(follower=viewer, following=viewed_owner)
    make_follow(follower=viewer, following=unviewed_owner)
    viewed_owner_older = make_story(viewed_owner)
    viewed_owner_newer = make_story(viewed_owner)
    unviewed_owner_story = make_story(unviewed_owner)
    service = StoryService()

    service.mark_viewed(viewed_owner_newer, viewer)

    groups = service.get_feed_stories(viewer)
    assert [group.owner for group in groups] == [unviewed_owner, viewed_owner]
    assert groups[0].is_viewed is False
    assert groups[1].is_viewed is True
    assert [item.story for item in groups[1].stories] == [
        viewed_owner_newer,
        viewed_owner_older,
    ]
    assert [item.is_viewed for item in groups[1].stories] == [True, False]
    # The unviewed group's stories are untouched by the viewer's viewing.
    assert all(not item.is_viewed for item in groups[0].stories)
    assert groups[0].stories[0].story == unviewed_owner_story


def test_repeated_view_is_idempotent():
    """Scenario: Repeated view is idempotent — marking the same story again
    does not create a duplicate view record."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    story = make_story(owner)
    service = StoryService()

    first = service.mark_viewed(story, viewer)
    second = service.mark_viewed(story, viewer)

    assert first.pk == second.pk
    assert StoryView.objects.filter(story=story, viewer=viewer).count() == 1
    assert service.is_viewed(story, viewer) is True


def test_cleanup_expired_deletes_stories_and_view_records():
    """Scenario: Management command cleanup (service level) — the cleanup
    deletes every expired story, reports the number of stories deleted, and
    the view records cascade with their story."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    expired = make_expired_story(owner)
    expired_view = StoryView.objects.create(story=expired, viewer=viewer)
    active = make_story(owner)
    service = StoryService()

    deleted = service.cleanup_expired()

    assert deleted == 1
    assert not Story.objects.filter(pk=expired.pk).exists()
    # The view record cascaded with its story (FK on_delete=CASCADE).
    assert not StoryView.objects.filter(pk=expired_view.pk).exists()
    assert list(Story.objects.all()) == [active]
    # A second run has nothing left to delete and reports zero.
    assert service.cleanup_expired() == 0
