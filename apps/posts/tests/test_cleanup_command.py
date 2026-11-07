"""Tests for the cleanup_expired_stories management command (task 5.2,
design decision 6): the command deletes the expired stories through
``StoryService.cleanup_expired`` and reports the deleted count."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.posts.models import Story, StoryView

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_media_root(tmp_path, settings):
    """Keep generated placeholder files inside a per-test media root."""
    settings.MEDIA_ROOT = tmp_path


def make_user(username: str):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="sup3r-secret-pw"
    )


def make_story(owner, *, expired: bool = False):
    """Create a story with a real image file; an explicit ``expires_at`` is
    respected by the model save-guard (same helper style as the story
    service tests)."""
    import io

    from django.core.files.base import ContentFile

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 40, 200)).save(buffer, format="JPEG")
    story = Story(owner=owner)
    if expired:
        story.expires_at = timezone.now() - timedelta(hours=1)
    story.image.save("story.jpg", ContentFile(buffer.getvalue()), save=False)
    story.save()
    return story


def test_cleanup_command_deletes_expired_stories_and_reports_count(capsys):
    """Scenario: Management command cleanup — with expired stories present
    the command deletes them (view records cascade) and reports the number
    deleted."""
    owner = make_user("alice")
    viewer = make_user("bob")
    expired_one = make_story(owner, expired=True)
    expired_two = make_story(owner, expired=True)
    active = make_story(owner)
    StoryView.objects.create(story=expired_one, viewer=viewer)

    call_command("cleanup_expired_stories")

    out = capsys.readouterr().out
    assert "Deleted 2 expired stories." in out
    assert not Story.objects.filter(pk__in=[expired_one.pk, expired_two.pk]).exists()
    # The view record cascaded with its story (spec: Expired story cleanup).
    assert not StoryView.objects.filter(story=expired_one).exists()
    # Active stories are untouched.
    assert Story.objects.filter(pk=active.pk).exists()


def test_cleanup_command_reports_zero_without_expired_stories(capsys):
    """With no expired stories present the command deletes nothing and
    reports a count of 0."""
    owner = make_user("alice")
    make_story(owner)

    call_command("cleanup_expired_stories")

    assert "Deleted 0 expired stories." in capsys.readouterr().out
    assert Story.objects.count() == 1
