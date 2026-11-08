"""Web stories surface: creation, stories bar and view tracking
(stories: "Story creation", "Stories bar on the home page",
"Story view tracking", "Stories bar ordering").
"""

import re
import uuid

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"
CREATE_URL = "/web/stories/create/"
VIEW_URL = "/web/stories/{story_id}/view/"
HX_REQUEST = {"HX-Request": "true"}

COMMENT_MARKERS = ("{#", "creation button plus one avatar", "carries `hx-swap-oob`")


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


def _avatar_state(html: str, username: str) -> str | None:
    match = re.search(rf'data-username="{username}"[^>]*data-viewed="(true|false)"', html)
    return match.group(1) if match else None


@pytest.mark.django_db
class TestStoryCreation:
    def test_successful_web_creation(self, client: Client) -> None:
        alice = _register(client, "alice")
        _login(client, "alice")

        response = client.post(CREATE_URL, headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert "Story created" in html
        assert 'hx-swap-oob="true"' in html
        assert 'id="stories-bar"' in html
        story = Story.objects.get(owner=alice)
        assert "stories/" in story.image.name
        assert story.media_type == "image"
        story.image.delete(save=False)

    def test_unauthenticated_creation_rejected(self, client: Client) -> None:
        response = client.post(CREATE_URL)

        assert response.status_code == 302
        assert LOGIN_URL in response["Location"]
        assert Story.objects.count() == 0

    def test_non_htmx_creation_redirects_to_the_feed(self, client: Client) -> None:
        alice = _register(client, "alice")
        _login(client, "alice")

        response = client.post(CREATE_URL)

        assert response.status_code == 302
        assert response["Location"] == FEED_URL
        story = Story.objects.get(owner=alice)
        assert "stories/" in story.image.name
        story.image.delete(save=False)


@pytest.mark.django_db
class TestStoryViewTracking:
    def test_first_view_recorded(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        story = _create_story(bob)
        _login(client, "alice")

        response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert "Story viewed" in html
        assert 'id="stories-bar"' in html
        assert StoryView.objects.filter(story=story, viewer=alice).count() == 1

    def test_repeated_view_is_idempotent(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        story = _create_story(bob)
        _login(client, "alice")
        client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert response.status_code == 200
        assert "Story viewed" in response.content.decode()
        assert StoryView.objects.filter(story=story, viewer=alice).count() == 1

    def test_self_view_rejected(self, client: Client) -> None:
        alice = _register(client, "alice")
        story = _create_story(alice)
        _login(client, "alice")

        response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert "You cannot view your own story" in html
        assert 'id="stories-bar"' in html
        assert StoryView.objects.count() == 0

    def test_non_followed_story_not_viewable(self, client: Client) -> None:
        mallory = _register(client, "mallory")
        _register(client, "alice")
        story = _create_story(mallory)
        _login(client, "alice")

        response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert "You can only view stories from people you follow" in html
        assert 'id="stories-bar"' in html
        assert StoryView.objects.count() == 0

    def test_unknown_or_expired_story_rejected(self, client: Client) -> None:
        from django.utils import timezone

        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        expired = _create_story(bob)
        Story.objects.filter(pk=expired.pk).update(expires_at=timezone.now())
        _login(client, "alice")

        unknown_response = client.post(VIEW_URL.format(story_id=uuid.uuid4()), headers=HX_REQUEST)
        expired_response = client.post(VIEW_URL.format(story_id=expired.pk), headers=HX_REQUEST)

        assert unknown_response.status_code == 200
        assert "Story not found" in unknown_response.content.decode()
        assert expired_response.status_code == 200
        assert "Story not found" in expired_response.content.decode()
        assert StoryView.objects.count() == 0

    def test_malformed_story_identifier_responds_404(self, client: Client) -> None:
        _register(client, "alice")
        _login(client, "alice")

        response = client.post("/web/stories/not-a-uuid/view/")

        assert response.status_code == 404
        assert StoryView.objects.count() == 0

    def test_non_htmx_view_redirects_to_the_feed(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        story = _create_story(bob)
        _login(client, "alice")

        response = client.post(VIEW_URL.format(story_id=story.pk))

        assert response.status_code == 302
        assert response["Location"] == FEED_URL
        assert StoryView.objects.filter(story=story, viewer=alice).count() == 1


@pytest.mark.django_db
class TestStoriesBar:
    def test_bar_lists_followed_users_with_active_stories(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        _create_story(bob)
        _login(client, "alice")

        response = client.post(CREATE_URL, headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert _avatar_state(html, "bob") == "false"
        assert 'data-testid="story-username">bob</span>' in html

    def test_bar_excludes_non_followed_users(self, client: Client) -> None:
        mallory = _register(client, "mallory")
        _register(client, "alice")
        _create_story(mallory)
        _login(client, "alice")

        response = client.post(CREATE_URL, headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-username="mallory"' not in html
        assert "mallory" not in html

    def test_bar_empty_without_followings(self, client: Client) -> None:
        _register(client, "alice")
        _login(client, "alice")

        response = client.post(CREATE_URL, headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert "Your story" in html
        assert 'data-testid="story-item"' not in html


@pytest.mark.django_db
class TestStoriesBarOrdering:
    def test_unviewed_groups_first(self, client: Client) -> None:
        bob = _register(client, "bob")
        carol = _register(client, "carol")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        FollowService().follow(follower=alice, following=carol)
        _create_story(bob)
        _create_story(carol)
        _login(client, "alice")
        bob_story = bob.stories.first()
        assert bob_story is not None

        response = client.post(VIEW_URL.format(story_id=bob_story.pk), headers=HX_REQUEST)

        assert response.status_code == 200
        html = response.content.decode()
        assert _avatar_state(html, "bob") == "true"
        assert _avatar_state(html, "carol") == "false"
        assert html.index('data-username="carol"') < html.index('data-username="bob"')

    def test_ring_updates_after_viewing(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        _create_story(bob)
        _login(client, "alice")

        before = client.post(CREATE_URL, headers=HX_REQUEST)
        assert _avatar_state(before.content.decode(), "bob") == "false"

        story = bob.stories.first()
        assert story is not None
        after = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert after.status_code == 200
        assert "Story viewed" in after.content.decode()
        assert _avatar_state(after.content.decode(), "bob") == "true"


@pytest.mark.django_db
class TestStoriesBarNoCommentLeak:
    """Regression: Django `{# ... #}` comments do not span multiple lines,
    so the stories-bar explanatory comment must never reach the rendered
    HTML of the feed page or of a story action response."""

    def test_feed_page_renders_no_stories_bar_comment_text(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        _create_story(bob)
        _login(client, "alice")

        response = client.get(FEED_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="stories-bar"' in html
        for marker in COMMENT_MARKERS:
            assert marker not in html

    def test_story_action_response_has_no_comment_text(self, client: Client) -> None:
        bob = _register(client, "bob")
        alice = _register(client, "alice")
        FollowService().follow(follower=alice, following=bob)
        story = _create_story(bob)
        _login(client, "alice")

        create_response = client.post(CREATE_URL, headers=HX_REQUEST)
        view_response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)

        assert create_response.status_code == 200
        assert "Story created" in create_response.content.decode()
        assert 'hx-swap-oob="true"' in create_response.content.decode()
        assert view_response.status_code == 200
        assert "Story viewed" in view_response.content.decode()
        assert 'hx-swap-oob="true"' in view_response.content.decode()
        for html in (create_response.content.decode(), view_response.content.decode()):
            for marker in COMMENT_MARKERS:
                assert marker not in html
