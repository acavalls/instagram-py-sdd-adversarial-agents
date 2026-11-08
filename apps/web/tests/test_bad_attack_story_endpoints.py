"""Bad-agent adversarial attacks on the web stories surface.

Attack surface: `POST /web/stories/create/`, `POST /web/stories/<uuid>/view/`
and the stories bar (stories: "Story creation", "Stories bar on the home
page", "Story view tracking", "Stories bar ordering", "Expired story
cleanup"; posts: "Post listing" feed/pagination interplay).
"""

import re
import uuid
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
CREATE_URL = "/web/stories/create/"
VIEW_URL = "/web/stories/{story_id}/view/"
FEED_URL = "/web/feed/"
HX_REQUEST = {"HX-Request": "true"}

ERROR_STORY_NOT_FOUND = "Story not found"
ERROR_SELF_VIEW = "You cannot view your own story"
ERROR_NOT_FOLLOWING = "You can only view stories from people you follow"


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


def _expire(story: Story, seconds_ago: int = 1) -> Story:
    """Force a story into the expired state via the raw queryset (ORM bypass)."""
    Story.objects.filter(pk=story.pk).update(
        expires_at=timezone.now() - timedelta(seconds=seconds_ago)
    )
    story.refresh_from_db()
    return story


def _avatar(html: str, username: str) -> str | None:
    match = re.search(rf'data-username="{username}"[^>]*data-viewed="(true|false)"', html)
    return match.group(1) if match else None


class StoryEndpointHardeningAttacks(TestCase):
    """Auth, CSRF, method and identifier-shape attacks on the story endpoints."""

    def test_bad_attack_story_create_requires_csrf(self) -> None:
        alice = _register(Client(), "alice")
        client = Client(enforce_csrf_checks=True)
        client.force_login(alice)
        response = client.post(CREATE_URL, headers=HX_REQUEST)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Story.objects.filter(owner=alice).count(), 0)

    def test_bad_attack_story_view_requires_csrf(self) -> None:
        alice = _register(Client(), "alice")
        bob = _register(Client(), "bob")
        FollowService().follow(follower=alice, following=bob)
        story = _create_story(bob)
        client = Client(enforce_csrf_checks=True)
        client.force_login(alice)
        response = client.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(StoryView.objects.filter(story=story, viewer=alice).count(), 0)

    def test_bad_attack_story_endpoints_reject_get(self) -> None:
        alice = _register(Client(), "alice")
        client = Client()
        client.force_login(alice)
        story = _create_story(alice)
        self.assertEqual(client.get(CREATE_URL, headers=HX_REQUEST).status_code, 405)
        self.assertEqual(
            client.get(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST).status_code, 405
        )

    def test_bad_attack_story_endpoints_reject_anonymous(self) -> None:
        client = Client()
        response = client.post(CREATE_URL, headers=HX_REQUEST)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Story.objects.count(), 0)
        response = client.post(VIEW_URL.format(story_id=uuid.uuid4()), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StoryView.objects.count(), 0)

    def test_bad_attack_story_view_unknown_uuid_toast_not_404(self) -> None:
        """A well-formed but unknown uuid answers the 'Story not found' toast (200)."""
        alice = _register(Client(), "alice")
        client = Client()
        client.force_login(alice)
        response = client.post(VIEW_URL.format(story_id=uuid.uuid4()), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertIn(ERROR_STORY_NOT_FOUND, response.content.decode())

    def test_bad_attack_story_view_malformed_uuid_is_404(self) -> None:
        """A non-uuid path segment never reaches the view (URL converter 404s)."""
        alice = _register(Client(), "alice")
        client = Client()
        client.force_login(alice)
        response = client.post("/web/stories/not-a-uuid/view/", headers=HX_REQUEST)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(StoryView.objects.count(), 0)


class StoryViewRuleAttacks(TestCase):
    """Attacks on the rejection rules and idempotency of view tracking."""

    def setUp(self) -> None:
        self.client_alice = Client()
        self.alice = _register(Client(), "alice")
        self.bob = _register(Client(), "bob")
        self.carol = _register(Client(), "carol")

    def test_bad_attack_view_expired_story_rejected_with_toast(self) -> None:
        FollowService().follow(follower=self.alice, following=self.bob)
        story = _expire(_create_story(self.bob))
        self.client_alice.force_login(self.alice)
        response = self.client_alice.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(ERROR_STORY_NOT_FOUND, html)
        self.assertNotIn("Story viewed", html)
        self.assertEqual(StoryView.objects.count(), 0)

    def test_bad_attack_view_own_story_rejected(self) -> None:
        story = _create_story(self.alice)
        self.client_alice.force_login(self.alice)
        response = self.client_alice.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(ERROR_SELF_VIEW, html)
        self.assertEqual(StoryView.objects.count(), 0)

    def test_bad_attack_view_non_followed_smuggled_story_rejected(self) -> None:
        """A story created directly by a non-followed user is never viewable."""
        story = _create_story(self.carol)  # alice does not follow carol
        self.client_alice.force_login(self.alice)
        response = self.client_alice.post(VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST)
        self.assertEqual(response.status_code, 200)
        self.assertIn(ERROR_NOT_FOLLOWING, response.content.decode())
        self.assertEqual(StoryView.objects.count(), 0)

    def test_bad_attack_view_post_burst_is_idempotent(self) -> None:
        """Five identical view POSTs record exactly one (story, viewer) row."""
        FollowService().follow(follower=self.alice, following=self.bob)
        story = _create_story(self.bob)
        self.client_alice.force_login(self.alice)
        for _ in range(5):
            response = self.client_alice.post(
                VIEW_URL.format(story_id=story.pk), headers=HX_REQUEST
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Story viewed", response.content.decode())
        self.assertEqual(StoryView.objects.filter(story=story, viewer=self.alice).count(), 1)


class StoriesBarIntegrityAttacks(TestCase):
    """Bar composition attacks: own stories, smuggled stories, huge groups."""

    def setUp(self) -> None:
        self.client_alice = Client()
        self.alice = _register(Client(), "alice")
        self.bob = _register(Client(), "bob")
        self.carol = _register(Client(), "carol")
        self.client_alice.force_login(self.alice)

    def _feed_html(self) -> str:
        response = self.client_alice.get(FEED_URL)
        assert response.status_code == 200
        return response.content.decode()

    def test_bad_attack_own_story_never_renders_as_bar_group(self) -> None:
        """The viewer's own active story shows only as 'Your story', never a group."""
        _create_story(self.alice)
        html = self._feed_html()
        self.assertIsNone(_avatar(html, "alice"))
        self.assertIn("Your story", html)
        self.assertNotIn('data-username="alice"', html)

    def test_bad_attack_smuggled_non_followed_story_never_in_bar(self) -> None:
        """A directly-created story of a non-followed user never leaks into the bar."""
        _create_story(self.carol)
        html = self._feed_html()
        self.assertNotIn('data-username="carol"', html)
        self.assertEqual(StoryView.objects.count(), 0)

    def test_bad_attack_hundred_story_group_single_avatar_newest_first(self) -> None:
        """100 stories from one followee render exactly one avatar in creation order."""
        FollowService().follow(follower=self.alice, following=self.bob)
        base = timezone.now()
        stories = [
            Story(
                owner=self.bob,
                created_at=base - timedelta(minutes=100 - index),
                expires_at=base - timedelta(minutes=100 - index) + timedelta(hours=24),
            )
            for index in range(100)
        ]
        Story.objects.bulk_create(stories)
        html = self._feed_html()
        # bob only; "Your story" uses story-add, not story-avatar
        self.assertEqual(html.count('data-testid="story-avatar"'), 1)
        self.assertEqual(html.count('data-username="bob"'), 1)
        output = StoryService().get_feed_stories(self.alice)
        self.assertEqual(len(output), 1)
        group = output[0]
        self.assertEqual(len(group.stories), 100)
        created = [entry.story.created_at for entry in group.stories]
        self.assertEqual(created, sorted(created, reverse=True))

    def test_bad_attack_unviewed_group_precedes_viewed_group(self) -> None:
        FollowService().follow(follower=self.alice, following=self.bob)
        FollowService().follow(follower=self.alice, following=self.carol)
        _create_story(self.bob)
        carol_story = _create_story(self.carol)
        StoryView.objects.create(story=carol_story, viewer=self.alice)
        html = self._feed_html()
        bob_pos = html.find('data-username="bob"')
        carol_pos = html.find('data-username="carol"')
        self.assertLess(bob_pos, carol_pos)
        self.assertEqual(_avatar(html, "bob"), "false")
        self.assertEqual(_avatar(html, "carol"), "true")
        # Viewing bob's latest story flips his ring on the next render.
        bob_story = Story.objects.filter(owner=self.bob).first()
        assert bob_story is not None
        self.client_alice.post(VIEW_URL.format(story_id=bob_story.pk), headers=HX_REQUEST)
        html = self._feed_html()
        self.assertEqual(_avatar(html, "bob"), "true")


class StoryCleanupAttacks(TestCase):
    """Purge attacks: only expired stories die, the command is idempotent."""

    def setUp(self) -> None:
        self.alice = _register(Client(), "alice")
        self.bob = _register(Client(), "bob")
        FollowService().follow(follower=self.alice, following=self.bob)

    def test_bad_attack_purge_keeps_active_story_and_its_views(self) -> None:
        active = _create_story(self.bob)
        StoryView.objects.create(story=active, viewer=self.alice)
        expired = _expire(_create_story(self.bob))
        StoryView.objects.create(story=expired, viewer=self.alice)
        client = Client()
        client.force_login(self.alice)
        response = client.get(FEED_URL)  # lazy purge on home render
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Story.objects.filter(pk=expired.pk).exists())
        self.assertTrue(Story.objects.filter(pk=active.pk).exists())
        self.assertTrue(StoryView.objects.filter(story=active, viewer=self.alice).exists())
        self.assertFalse(StoryView.objects.filter(story=expired).exists())

    def test_bad_attack_cleanup_command_is_idempotent(self) -> None:
        _expire(_create_story(self.bob))
        first, second = StringIO(), StringIO()
        call_command("cleanup_expired_stories", stdout=first)
        call_command("cleanup_expired_stories", stdout=second)
        self.assertIn("Deleted 1 expired stories.", first.getvalue())
        self.assertIn("Deleted 0 expired stories.", second.getvalue())
        self.assertEqual(Story.objects.count(), 0)

    def test_bad_attack_purge_does_not_break_feed_pagination(self) -> None:
        """Lazy purge during home render leaves the posts pagination intact."""
        from apps.posts.models import Post

        Post.objects.create(owner=self.bob, caption="post one")
        Post.objects.create(owner=self.bob, caption="post two")
        _expire(_create_story(self.bob))
        client = Client()
        client.force_login(self.alice)
        full = client.get(FEED_URL, {"page": 1})  # non-HTMX full page with page param
        self.assertEqual(full.status_code, 200)
        html = full.content.decode()
        self.assertIn("post one", html)
        self.assertIn("post two", html)
        self.assertEqual(Story.objects.count(), 0)  # purge ran during the render
