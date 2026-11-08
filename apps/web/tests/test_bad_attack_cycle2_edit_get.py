"""The Bad — cycle-2 attacks on the posts ownership fix surface and web edges.

BUG-002 (cycle 1) fixed the ownership check in GetPostUseCase for the card
fragment and the API detail. This file re-attacks the fix from angles cycle
1 could not cover: every other web path that touches a post id, plus feed
pagination windows with many posts.
"""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"


def _register_and_login(client: Client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _create_post(user: User, caption: str = "hello") -> Post:
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(user=user, caption=caption)
    )
    assert output.success and output.post is not None
    return output.post


@pytest.mark.django_db
class TestOwnershipAcrossWebPaths:
    def test_non_owner_get_edit_form_does_not_render_the_post(self, client) -> None:
        owner = _register_and_login(client, "ownered")
        post = _create_post(owner, caption="secret caption")
        intruder = _register_and_login(client, "intrudered")

        response = client.get(f"/web/posts/{post.pk}/edit/")

        assert intruder.username == "intrudered"
        assert response.status_code == 404
        assert b"secret caption" not in response.content

    def test_non_owner_post_edit_is_still_forbidden(self, client) -> None:
        owner = _register_and_login(client, "ownerpost")
        post = _create_post(owner)
        _register_and_login(client, "intruderpost")

        response = client.post(f"/web/posts/{post.pk}/edit/", {"caption": "hacked"})

        assert response.status_code == 403
        assert Post.objects.get(pk=post.pk).caption == "hello"

    def test_non_owner_get_card_is_404_not_200(self, client) -> None:
        owner = _register_and_login(client, "ownercard")
        post = _create_post(owner)
        _register_and_login(client, "intrudercard")

        response = client.get(f"/web/posts/{post.pk}/card/")

        assert response.status_code == 404

    def test_owner_still_gets_the_edit_form(self, client) -> None:
        owner = _register_and_login(client, "ownerown")
        post = _create_post(owner, caption="mine")

        response = client.get(f"/web/posts/{post.pk}/edit/")

        assert response.status_code == 200
        assert b"mine" in response.content


@pytest.mark.django_db
class TestFeedWindowsWithManyPosts:
    def test_htmx_window_is_stable_across_hostile_page_params(self, client) -> None:
        author = _register_and_login(client, "feedauthor")
        for index in range(25):
            _create_post(author, caption=f"post {index}")
        viewer = _register_and_login(client, "feedheavy")
        FollowService().follow(follower=viewer, following=author)

        first = client.get(FEED_URL, HTTP_HX_REQUEST="true")
        second = client.get(f"{FEED_URL}?page=2", HTTP_HX_REQUEST="true")
        garbage = client.get(f"{FEED_URL}?page=not-a-number", HTTP_HX_REQUEST="true")
        beyond = client.get(f"{FEED_URL}?page=99", HTTP_HX_REQUEST="true")

        assert first.status_code == 200
        assert second.status_code == 200
        assert garbage.status_code == 200
        assert beyond.status_code == 200
        assert b"post 24" in first.content
        assert b"post 12" in second.content
        assert b"post 13" not in second.content
        assert b"post 24" in garbage.content
        assert b"post-card" not in beyond.content
