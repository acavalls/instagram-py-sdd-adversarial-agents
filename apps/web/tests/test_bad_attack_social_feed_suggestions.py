"""Bad attack (GBU): feed and suggestions integrity through the web UI.

Attacks the "Followed-users feed" and "User suggestions" requirements:
leak-after-unfollow, pagination windows crossing the follow set, large
follow subqueries, primary/secondary empty-state transitions, and the
self/followed exclusions of the suggestions panel.
"""

import re
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

REGISTER_URL = "/web/register/"
LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"

CAPTION_PREFIX = "feedleak"


def _register_and_login(client: Client, username: str) -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _login(client: Client, username: str) -> User:
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _create_post(user: User, caption: str, minutes_ago: int) -> Post:
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(
            user=user,
            caption=caption,
            media=(PostMediaInput(file=ContentFile(b"data", name="m.png"), media_type="image"),),
        )
    )
    assert output.success and output.post is not None
    Post.objects.filter(pk=output.post.pk).update(
        created_at=timezone.now() - timedelta(minutes=minutes_ago)
    )
    return output.post


def _card_captions(html: str) -> list[str]:
    """The attacked captions in their order of appearance in the HTML."""
    return re.findall(rf"({CAPTION_PREFIX}[\w-]+)", html)


def _follow(client: Client, viewer: User, target: User) -> None:
    response = client.post(f"/web/profile/{target.pk}/follow/", headers={"HX-Request": "true"})
    assert response.status_code == 200


def _unfollow(client: Client, viewer: User, target: User) -> None:
    response = client.post(f"/web/profile/{target.pk}/unfollow/", headers={"HX-Request": "true"})
    assert response.status_code == 200


def _suggestion_usernames(html: str) -> list[str]:
    return re.findall(
        r'data-testid="suggestion-username">(\w+)</a>',
        html,
    )


class TestBadAttackFeedLeakAfterUnfollow:
    def test_bad_attack_unfollowed_user_posts_vanish_from_every_window(
        self, client: Client
    ) -> None:
        """A user unfollowed between page loads must not leak their posts
        into any later feed window."""
        alice = _register_and_login(client, "leakalice")
        bob = _register_and_login(client, "leakbob")
        for minutes in range(30, 5, -1):
            _create_post(bob, f"{CAPTION_PREFIX}-bob-{minutes}", minutes_ago=minutes)
        _login(client, "leakalice")
        _follow(client, alice, bob)

        first = client.get(FEED_URL)
        assert len(_card_captions(first.content.decode())) == 12
        _unfollow(client, alice, bob)

        for page in (1, 2, 3):
            response = client.get(f"{FEED_URL}?page={page}", headers={"HX-Request": "true"})
            html = response.content.decode()
            assert "leak-bob" not in html, f"bob's posts leaked on page {page}"

        assert not FollowService().is_following(alice, bob)


class TestBadAttackFeedPaginationWindows:
    def test_bad_attack_window_crossing_covers_all_posts_without_duplicates(
        self, client: Client
    ) -> None:
        """Pages crossing the follow set must tile the whole feed exactly
        once, globally newest first."""
        alice = _register_and_login(client, "pagealice")
        bob = _register_and_login(client, "pagebob")
        carol = _register_and_login(client, "pagecarol")

        expected: list[str] = []
        for minutes in range(25, 0, -1):
            owner = bob if minutes % 2 else carol
            expected.append(f"{CAPTION_PREFIX}-{owner.username}-{minutes}")
            _create_post(owner, f"{CAPTION_PREFIX}-{owner.username}-{minutes}", minutes_ago=minutes)
        expected.reverse()  # newest first

        _login(client, "pagealice")
        _follow(client, alice, bob)
        _follow(client, alice, carol)

        seen: list[str] = []
        for page in (1, 2, 3):
            response = client.get(f"{FEED_URL}?page={page}", headers={"HX-Request": "true"})
            assert response.status_code == 200
            seen.extend(_card_captions(response.content.decode()))

        assert seen == expected, "feed windows are not a clean tiling of the followed posts"

    def test_bad_attack_large_follow_set_subquery(self, client: Client) -> None:
        """Following many users still yields a correct newest-first window."""
        alice = _register_and_login(client, "manyalice")
        followed_users = []
        for index in range(50):
            followed = _register_and_login(client, f"manyu{index}")
            _create_post(followed, f"{CAPTION_PREFIX}-many-{index}", minutes_ago=100 - index)
            followed_users.append(followed)
        _login(client, "manyalice")
        for followed in followed_users:
            _follow(client, alice, followed)

        response = client.get(FEED_URL, headers={"HX-Request": "true"})
        captions = _card_captions(response.content.decode())

        assert response.status_code == 200
        assert len(captions) == 12
        indices = [int(c.rsplit("-", 1)[1]) for c in captions]
        assert indices == sorted(indices, reverse=True), "not newest first"

    def test_bad_attack_empty_state_transitions(self, client: Client) -> None:
        """Primary -> secondary -> primary empty state transitions."""
        alice = _register_and_login(client, "emptyalice")
        quiet_bob = _register_and_login(client, "emptybob")
        _login(client, "emptyalice")

        response = client.get(FEED_URL)
        html = response.content.decode()
        assert 'data-testid="feed-empty"' in html
        assert "Share Photos" in html

        _follow(client, alice, quiet_bob)
        response = client.get(FEED_URL)
        html = response.content.decode()
        assert 'data-testid="feed-empty-secondary"' in html
        assert "No posts from the people you follow yet." in html

        _unfollow(client, alice, quiet_bob)
        response = client.get(FEED_URL)
        html = response.content.decode()
        assert 'data-testid="feed-empty"' in html
        assert 'data-testid="feed-empty-secondary"' not in html


class TestBadAttackSuggestionsIntegrity:
    def test_bad_attack_suggestions_never_self(self, client: Client) -> None:
        alice = _register_and_login(client, "suggalice")
        response = client.get(FEED_URL)
        usernames = _suggestion_usernames(response.content.decode())
        assert alice.username not in usernames

    def test_bad_attack_suggestions_refresh_after_endpoint_follow(self, client: Client) -> None:
        """A user followed through the endpoint mid-session disappears
        from the next suggestions render."""
        alice = _register_and_login(client, "suggbalice")
        bob = _register_and_login(client, "suggbbob")
        _register_and_login(client, "suggbcarol")
        _login(client, "suggbalice")

        html = client.get(FEED_URL).content.decode()
        assert set(_suggestion_usernames(html)) == {"suggbbob", "suggbcarol"}

        _follow(client, alice, bob)
        html = client.get(FEED_URL).content.decode()
        usernames = _suggestion_usernames(html)
        assert "suggbbob" not in usernames
        assert "suggbcarol" in usernames

    def test_bad_attack_suggestions_empty_after_following_everyone(self, client: Client) -> None:
        alice = _register_and_login(client, "suggealice")
        others = [_register_and_login(client, f"suggeu{i}") for i in range(3)]
        _login(client, "suggealice")
        for other in others:
            _follow(client, alice, other)

        response = client.get(FEED_URL)
        html = response.content.decode()
        assert "No suggestions right now." in html
        assert _suggestion_usernames(html) == []
