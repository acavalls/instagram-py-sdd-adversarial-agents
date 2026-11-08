"""Expired-story cleanup through the home page render
(stories: "Expired story cleanup" — "Lazy purge on home render").
"""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.social.services import FollowService

FEED_URL = "/web/feed/"
LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"


def _register(client: Client, username: str) -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    return User.objects.get(username=username)


def _login(client: Client, username: str) -> None:
    client.post(LOGIN_URL, {"username": username, "password": "password123"})


def _create_story(owner: User) -> Story:
    output = StoryService().create(owner=owner)
    assert output.success and output.story is not None
    return output.story


def _expire(story: Story) -> None:
    Story.objects.filter(pk=story.pk).update(expires_at=timezone.now() - timedelta(hours=1))


def _cleanup_media() -> None:
    for story in Story.objects.all():
        story.image.delete(save=False)


@pytest.mark.django_db
class TestLazyPurgeOnHomeRender:
    def test_lazy_purge_on_home_render(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        expired = _create_story(bob)
        StoryView.objects.create(story=expired, viewer=alice)
        active = _create_story(bob)
        _expire(expired)
        assert Story.objects.count() == 2
        assert StoryView.objects.count() == 1
        _login(client, "alice")

        try:
            response = client.get(FEED_URL)
        finally:
            _cleanup_media()

        assert response.status_code == 200
        html = response.content.decode()
        assert not Story.objects.filter(pk=expired.pk).exists()
        assert not StoryView.objects.filter(story=expired).exists()
        assert Story.objects.filter(pk=active.pk).exists()
        assert 'data-username="bob"' in html
        assert 'data-testid="story-item"' in html

    def test_purged_story_never_reaches_the_bar(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        expired = _create_story(bob)
        _expire(expired)
        _login(client, "alice")

        try:
            response = client.get(FEED_URL)
        finally:
            _cleanup_media()

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="story-item"' not in html
        assert 'data-username="bob"' not in html
        assert Story.objects.count() == 0
        assert StoryView.objects.count() == 0
