import re
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"


def _register_and_login(client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
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


def _card_ids(html: str) -> list[str]:
    return re.findall(r'data-testid="post-card" id="post-([0-9a-f-]+)"', html)


@pytest.mark.django_db
class TestFeedView:
    def test_placeholder_requires_login(self, client) -> None:
        response = client.get(FEED_URL)

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)

    def test_personal_feed_on_the_feed_page(self, client) -> None:
        user = _register_and_login(client)
        oldest = _create_post(user, caption="oldest post")
        newest = _create_post(user, caption="newest post")
        _set_created_at(oldest, minutes_ago=10)
        _set_created_at(newest, minutes_ago=1)

        response = client.get(FEED_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="feed"' in html
        assert _card_ids(html) == [str(newest.pk), str(oldest.pk)]
        assert "newest post" in html
        assert "oldest post" in html
        assert 'data-testid="post-username"' in html
        assert ">alice</a>" in html
        assert 'data-testid="post-media-image"' in html
        assert "post_media/" in html
        assert 'data-testid="post-timestamp"' in html

    def test_home_feed_loads_more_posts_on_scroll(self, client) -> None:
        user = _register_and_login(client)
        posts = [_create_post(user, caption=f"post {index}") for index in range(12)]
        for index, post in enumerate(posts):
            _set_created_at(post, minutes_ago=60 - index)

        first_page = client.get(FEED_URL).content.decode()
        assert len(_card_ids(first_page)) == 10
        assert 'data-testid="feed-sentinel"' in first_page
        assert "page=2" in first_page
        assert 'data-testid="feed-end"' not in first_page

        response = client.get(f"{FEED_URL}?page=2", headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert "<html" not in html
        assert 'data-testid="sidebar"' not in html
        assert 'data-testid="feed"' not in html
        assert _card_ids(html) == [str(post.pk) for post in list(reversed(posts))[10:]]
        first_page_ids = set(_card_ids(first_page))
        assert not first_page_ids.intersection(_card_ids(html))
        assert 'data-testid="feed-end"' in html
        assert 'data-testid="feed-sentinel"' not in html

    def test_non_htmx_request_with_a_page_parameter_renders_the_full_page(self, client) -> None:
        user = _register_and_login(client)
        posts = [_create_post(user, caption=f"post {index}") for index in range(12)]
        for index, post in enumerate(posts):
            _set_created_at(post, minutes_ago=60 - index)

        response = client.get(f"{FEED_URL}?page=2")

        assert response.status_code == 200
        html = response.content.decode()
        assert "<html" in html
        assert 'data-testid="sidebar"' in html
        assert _card_ids(html) == [str(post.pk) for post in list(reversed(posts))[10:]]
        assert 'data-testid="feed-end"' in html

    def test_feed_without_posts_shows_the_empty_state(self, client) -> None:
        _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="feed-empty"' in html
        assert "No posts yet" in html
