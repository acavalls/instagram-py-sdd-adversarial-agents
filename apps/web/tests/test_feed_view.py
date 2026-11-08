import re
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post, Story
from apps.posts.services import PostMediaInput, PostService, StoryService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"
FEED_PAGE_SIZE = 12


def _register_and_login(client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _login(client, username: str) -> User:
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _create_post(user: User, caption: str = "hello", media_count: int = 1) -> Post:
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(
            user=user,
            caption=caption,
            media=(PostMediaInput(file=ContentFile(b"data", name="media.png"), media_type="image"),)
            * media_count,
        )
    )
    assert output.success and output.post is not None
    return output.post


def _set_created_at(post: Post, minutes_ago: int) -> None:
    Post.objects.filter(pk=post.pk).update(
        created_at=timezone.now() - timedelta(minutes=minutes_ago)
    )


def _follow(follower: User, following: User) -> None:
    FollowService().follow(follower=follower, following=following)


def _create_story(owner: User) -> Story:
    output = StoryService().create(owner=owner)
    assert output.success and output.story is not None
    return output.story


def _cleanup_story_media() -> None:
    for story in Story.objects.all():
        story.image.delete(save=False)


def _card_ids(html: str) -> list[str]:
    return re.findall(r'data-testid="post-card" id="post-([0-9a-f-]+)"', html)


@pytest.mark.django_db
class TestFeedLanding:
    def test_placeholder_requires_login(self, client) -> None:
        response = client.get(FEED_URL)

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)

    def test_logged_in_user_reaches_the_placeholder(self, client) -> None:
        author = _register_and_login(client, "bob")
        _create_post(author, caption="bob post")
        _register_and_login(client)
        _follow(User.objects.get(username="alice"), author)

        response = client.get(FEED_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="feed"' in html
        assert 'data-testid="post-card"' in html
        assert "bob post" in html


@pytest.mark.django_db
class TestFeedContent:
    def test_personal_feed_on_the_feed_page(self, client) -> None:
        user = _register_and_login(client)
        author = _register_and_login(client, "bob")
        stranger = _register_and_login(client, "carol")
        _follow(user, author)
        oldest = _create_post(author, caption="bob oldest")
        newest = _create_post(author, caption="bob newest")
        stranger_post = _create_post(stranger, caption="stranger post")
        own_post = _create_post(user, caption="own post")
        _set_created_at(oldest, minutes_ago=10)
        _set_created_at(newest, minutes_ago=1)
        _set_created_at(stranger_post, minutes_ago=5)
        _set_created_at(own_post, minutes_ago=3)
        _login(client, "alice")

        response = client.get(FEED_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="feed"' in html
        assert _card_ids(html) == [str(newest.pk), str(oldest.pk)]
        assert "bob newest" in html
        assert "bob oldest" in html
        assert ">bob</a>" in html
        assert 'data-testid="post-username"' in html
        assert 'data-testid="post-media-image"' in html
        assert "post_media/" in html
        assert 'data-testid="post-timestamp"' in html
        assert "stranger post" not in html
        assert "own post" not in html
        assert 'data-testid="post-username">alice</a>' not in html

    def test_feed_renders_the_stories_bar_above_the_post_list(self, client) -> None:
        user = _register_and_login(client)
        author = _register_and_login(client, "bob")
        _follow(user, author)
        _create_post(author, caption="bob post")
        _create_story(author)
        _login(client, "alice")

        try:
            response = client.get(FEED_URL)
        finally:
            _cleanup_story_media()

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="stories-bar"' in html
        assert 'data-username="bob"' in html
        assert html.index('data-testid="stories-bar"') < html.index('data-testid="post-card"')

    def test_home_feed_loads_more_posts_on_scroll(self, client) -> None:
        user = _register_and_login(client)
        first_author = _register_and_login(client, "bob")
        second_author = _register_and_login(client, "carol")
        _follow(user, first_author)
        _follow(user, second_author)
        posts = []
        for index in range(14):
            author = first_author if index % 2 == 0 else second_author
            posts.append(_create_post(author, caption=f"post {index}"))
        for index, post in enumerate(posts):
            _set_created_at(post, minutes_ago=120 - index)
        _login(client, "alice")

        first_page = client.get(FEED_URL).content.decode()

        assert len(_card_ids(first_page)) == FEED_PAGE_SIZE
        assert _card_ids(first_page) == [str(post.pk) for post in list(reversed(posts))[:12]]
        assert 'data-testid="feed-sentinel"' in first_page
        assert "page=2" in first_page
        assert 'data-testid="feed-end"' not in first_page

        response = client.get(f"{FEED_URL}?page=2", headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert "<html" not in html
        assert 'data-testid="sidebar"' not in html
        assert 'data-testid="feed"' not in html
        assert _card_ids(html) == [str(post.pk) for post in list(reversed(posts))[12:]]
        assert not set(_card_ids(first_page)).intersection(_card_ids(html))
        assert 'data-testid="feed-end"' in html
        assert 'data-testid="feed-sentinel"' not in html

    def test_non_htmx_request_with_a_page_parameter_renders_the_full_page(self, client) -> None:
        user = _register_and_login(client)
        author = _register_and_login(client, "bob")
        _follow(user, author)
        posts = [_create_post(author, caption=f"post {index}") for index in range(14)]
        for index, post in enumerate(posts):
            _set_created_at(post, minutes_ago=120 - index)
        _login(client, "alice")

        response = client.get(f"{FEED_URL}?page=2")

        assert response.status_code == 200
        html = response.content.decode()
        assert "<html" in html
        assert 'data-testid="sidebar"' in html
        assert _card_ids(html) == [str(post.pk) for post in list(reversed(posts))[12:]]
        assert 'data-testid="feed-end"' in html


@pytest.mark.django_db
class TestFeedEmptyStates:
    def test_empty_feed_state(self, client) -> None:
        _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="feed-empty"' in html
        assert "Share Photos" in html
        assert "Follow people to see their photos here, or share your first one." in html
        assert 'data-testid="feed-empty-cta"' in html
        assert 'action="/web/posts/create/"' in html
        assert 'data-testid="post-card"' not in html

    def test_feed_with_follows_but_no_posts_shows_the_secondary_empty_state(self, client) -> None:
        user = _register_and_login(client)
        author = _register_and_login(client, "bob")
        _follow(user, author)
        _login(client, "alice")

        html = client.get(FEED_URL).content.decode()

        assert "No posts from the people you follow yet." in html
        assert 'data-testid="feed-empty-secondary"' in html
        assert 'data-testid="post-card"' not in html
        assert "Share Photos" not in html
        assert 'data-testid="feed-empty"' not in html
