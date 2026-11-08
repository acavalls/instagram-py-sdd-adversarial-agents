"""The Bad — attack tests for the posts web surface and media generator."""

import pytest
from django.core.files.base import ContentFile
from django.test import Client

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia
from apps.posts.services import PostService
from apps.posts.services.media_generator import generate_placeholder_image
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
class TestCsrfEnforcement:
    def test_create_post_without_csrf_token_is_rejected(self) -> None:
        user = User.objects.create(
            username="carol", email="carol@example.com", password="password123"
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post("/web/posts/create/")

        assert response.status_code == 403
        assert Post.objects.filter(owner=user).count() == 0


@pytest.mark.django_db
class TestFeedPageParameter:
    @pytest.mark.parametrize("page", ["0", "-1", "abc", "999999"])
    def test_hostile_page_values_do_not_crash_the_feed(self, client, page: str) -> None:
        user = _register_and_login(client)
        _create_post(user)

        response = client.get(f"{FEED_URL}?page={page}")

        assert response.status_code == 200


@pytest.mark.django_db
class TestWebAttackEdges:
    def test_htmx_delete_of_an_unknown_post_is_404(self, client) -> None:
        _register_and_login(client)
        response = client.post(
            "/web/posts/00000000-0000-0000-0000-000000000000/delete/",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404

    def test_htmx_delete_by_a_non_owner_is_403(self, client) -> None:
        owner = _register_and_login(client, "bob")
        post = _create_post(owner)
        _register_and_login(client, "alice")

        response = client.post(f"/web/posts/{post.pk}/delete/", headers={"HX-Request": "true"})

        assert response.status_code == 403
        assert Post.objects.filter(pk=post.pk).exists()

    def test_edit_get_of_an_unknown_post_is_404(self, client) -> None:
        _register_and_login(client)
        response = client.get("/web/posts/00000000-0000-0000-0000-000000000000/edit/")
        assert response.status_code == 404

    def test_edit_post_of_an_unknown_post_closes_the_form_without_changes(self, client) -> None:
        _register_and_login(client)
        response = client.post(
            "/web/posts/00000000-0000-0000-0000-000000000000/edit/",
            {"caption": "nope"},
        )
        assert response.status_code == 200
        assert response.content == b""

    def test_caption_html_is_escaped_in_the_card_fragment(self, client) -> None:
        user = _register_and_login(client)
        post = _create_post(user, caption='<script>alert(1)</script> & "quotes"')

        response = client.get(f"/web/posts/{post.pk}/card/")

        html = response.content.decode()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


@pytest.mark.django_db
class TestMediaGenerator:
    def test_same_seed_is_deterministic(self) -> None:
        first = generate_placeholder_image("same-seed")
        second = generate_placeholder_image("same-seed")
        assert first.read() == second.read()

    def test_same_filename_never_overwrites_an_existing_media_file(self) -> None:
        user = User.objects.create(
            username="dave", email="dave@example.com", password="password123"
        )
        post = Post.objects.create(owner=user)
        first = PostMedia(post=post, media_type="image", order=0)
        first.file.save("placeholder.png", ContentFile(b"one"), save=True)
        second = PostMedia(post=post, media_type="image", order=1)
        second.file.save("placeholder.png", ContentFile(b"two"), save=True)

        assert first.file.name is not None and second.file.name is not None
        assert first.file.name != second.file.name
        assert first.file.storage.exists(first.file.name)
        assert second.file.storage.exists(second.file.name)
