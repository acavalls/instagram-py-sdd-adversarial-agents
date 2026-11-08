"""The Bad — cycle-3 attacks on the ownership-aware web edit-form routing.

The fix routes the edit form (GET) and its validation-error re-render
(POST) through the ownership-aware GetPostUseCase. This file attacks the
remaining routing angles: the owner re-render after a refused caption,
the caption boundary through the web form, the anonymous-user edge on
every post path, and the check order (ownership before validation) on
the POST path.
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.posts.models import CAPTION_MAX_LENGTH, Post
from apps.posts.services import PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"


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
class TestOwnerEditReRender:
    def test_over_limit_caption_re_renders_the_form_and_keeps_the_post(
        self, client: Client
    ) -> None:
        owner = _register_and_login(client, "rerenderown")
        post = _create_post(owner, caption="original")

        response = client.post(
            reverse("web:post_edit", args=[post.pk]),
            {"caption": "x" * (CAPTION_MAX_LENGTH + 1)},
        )

        assert response.status_code == 200
        assert b"Caption cannot exceed 2200 characters" in response.content
        assert b"post-edit-form" in response.content
        assert Post.objects.get(pk=post.pk).caption == "original"

    def test_caption_exactly_2200_applies_and_confirms(self, client: Client) -> None:
        owner = _register_and_login(client, "boundaryown")
        post = _create_post(owner, caption="original")

        response = client.post(
            reverse("web:post_edit", args=[post.pk]),
            {"caption": "a" * CAPTION_MAX_LENGTH},
        )

        assert response.status_code == 200
        assert b"post-card" in response.content
        assert response["HX-Trigger"] == '{"toast": "Post updated!"}'
        assert Post.objects.get(pk=post.pk).caption == "a" * CAPTION_MAX_LENGTH

    def test_re_rendered_form_belongs_to_the_submitting_owner(self, client: Client) -> None:
        owner = _register_and_login(client, "formowner")
        post = _create_post(owner, caption="owners text")

        response = client.post(
            reverse("web:post_edit", args=[post.pk]),
            {"caption": "x" * (CAPTION_MAX_LENGTH + 1)},
        )

        assert response.status_code == 200
        assert b"owners text" in response.content


@pytest.mark.django_db
class TestCheckOrderOnPostPath:
    def test_non_owner_over_limit_caption_is_ownership_403_not_a_validation_error(
        self, client: Client
    ) -> None:
        owner = _register_and_login(client, "orderowner")
        post = _create_post(owner, caption="original")
        _register_and_login(client, "orderintruder")

        response = client.post(
            reverse("web:post_edit", args=[post.pk]),
            {"caption": "x" * (CAPTION_MAX_LENGTH + 1)},
        )

        assert response.status_code == 403
        assert b"You can only edit your own posts" in response.content
        assert Post.objects.get(pk=post.pk).caption == "original"


@pytest.mark.django_db
class TestAnonymousEdges:
    def test_anonymous_card_edit_get_and_edit_post_never_render_or_mutate(
        self, client: Client
    ) -> None:
        owner = _register_and_login(client, "anonowner")
        post = _create_post(owner, caption="private")
        client.logout()

        card = client.get(reverse("web:post_card", args=[post.pk]))
        edit_get = client.get(reverse("web:post_edit", args=[post.pk]))
        edit_post = client.post(reverse("web:post_edit", args=[post.pk]), {"caption": "hacked"})

        for response in (card, edit_get, edit_post):
            assert response.status_code == 302
            assert "/web/login/" in response["Location"]
            assert b"private" not in response.content
        assert Post.objects.get(pk=post.pk).caption == "private"
