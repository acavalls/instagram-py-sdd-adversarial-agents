import uuid

import pytest

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia
from apps.posts.services import PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"


def _register_and_login(client, username: str = "alice") -> User:
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
class TestPostDeletion:
    def test_web_deletion_removes_the_card(self, client) -> None:
        user = _register_and_login(client)
        post = _create_post(user)

        response = client.post(f"/web/posts/{post.pk}/delete/", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert response.content == b""
        assert "Post deleted!" in response.headers["HX-Trigger"]
        assert not Post.objects.filter(pk=post.pk).exists()
        assert not PostMedia.objects.filter(post_id=post.pk).exists()

    def test_web_deletion_without_htmx_redirects_to_the_feed(self, client) -> None:
        user = _register_and_login(client)
        post = _create_post(user)

        response = client.post(f"/web/posts/{post.pk}/delete/", follow=True)

        assert response.status_code == 200
        assert "Post deleted!" in response.content.decode()
        assert not Post.objects.filter(pk=post.pk).exists()

    def test_web_deletion_rejects_a_non_owner(self, client) -> None:
        owner = _register_and_login(client, "bob")
        post = _create_post(owner)
        _register_and_login(client, "alice")

        response = client.post(f"/web/posts/{post.pk}/delete/", headers={"HX-Request": "true"})

        assert response.status_code == 403
        assert "You can only delete your own posts" in response.content.decode()
        assert Post.objects.filter(pk=post.pk).exists()

    def test_web_deletion_of_an_unknown_post_returns_404(self, client) -> None:
        _register_and_login(client)

        response = client.post(f"/web/posts/{uuid.uuid4()}/delete/", headers={"HX-Request": "true"})

        assert response.status_code == 404
