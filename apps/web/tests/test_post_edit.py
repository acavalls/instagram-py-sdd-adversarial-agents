import uuid

import pytest

from apps.accounts.models import User
from apps.posts.models import Post
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


def _edit_url(post: Post) -> str:
    return f"/web/posts/{post.pk}/edit/"


@pytest.mark.django_db
class TestInlineEdit:
    def test_inline_web_edit(self, client) -> None:
        user = _register_and_login(client)
        post = _create_post(user, caption="old caption")

        form_response = client.get(_edit_url(post))
        assert form_response.status_code == 200
        form_html = form_response.content.decode()
        assert 'data-testid="post-edit-form"' in form_html
        assert "old caption" in form_html

        response = client.post(
            _edit_url(post), {"caption": "new caption"}, headers={"HX-Request": "true"}
        )

        assert response.status_code == 200
        html = response.content.decode()
        assert "new caption" in html
        assert 'data-testid="post-edit-form"' not in html
        assert 'data-testid="post-card"' in html
        assert "Post updated!" in response.headers["HX-Trigger"]
        post.refresh_from_db()
        assert post.caption == "new caption"

    def test_cancel_inline_edit(self, client) -> None:
        user = _register_and_login(client)
        post = _create_post(user, caption="kept caption")

        form_html = client.get(_edit_url(post)).content.decode()
        assert 'data-testid="post-edit-cancel"' in form_html

        card_response = client.get(f"/web/posts/{post.pk}/card/")
        assert card_response.status_code == 200
        card_html = card_response.content.decode()
        assert 'data-testid="post-card"' in card_html
        assert "kept caption" in card_html
        assert 'data-testid="post-edit-form"' not in card_html

        unknown_id = uuid.uuid4()
        response = client.post(
            f"/web/posts/{unknown_id}/edit/",
            {"caption": "should not apply"},
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
        assert response.content == b""
        post.refresh_from_db()
        assert post.caption == "kept caption"
        assert not Post.objects.filter(pk=unknown_id).exists()

    def test_web_edit_post_refuses_a_non_owner(self, client) -> None:
        owner = _register_and_login(client, "bob")
        post = _create_post(owner, caption="owner caption")
        _register_and_login(client, "alice")

        response = client.post(
            _edit_url(post), {"caption": "intruder caption"}, headers={"HX-Request": "true"}
        )

        assert response.status_code == 403
        assert "You can only edit your own posts" in response.content.decode()
        post.refresh_from_db()
        assert post.caption == "owner caption"


@pytest.mark.django_db
class TestEditFragmentsUnknownPost:
    def test_edit_form_for_an_unknown_post_returns_404(self, client) -> None:
        _register_and_login(client)

        response = client.get(f"/web/posts/{uuid.uuid4()}/edit/")

        assert response.status_code == 404

    def test_card_fragment_for_an_unknown_post_returns_404(self, client) -> None:
        _register_and_login(client)

        response = client.get(f"/web/posts/{uuid.uuid4()}/card/")

        assert response.status_code == 404


@pytest.mark.django_db
class TestEditFormVisibility:
    def test_web_edit_form_refuses_unknown_or_non_owner_posts(self, client) -> None:
        owner = _register_and_login(client, "formowner")
        post = _create_post(owner, caption="private caption")
        _register_and_login(client, "formintruder")

        unknown_response = client.get(f"/web/posts/{uuid.uuid4()}/edit/")
        non_owner_response = client.get(_edit_url(post))

        assert unknown_response.status_code == 404
        assert non_owner_response.status_code == 404
        assert b"private caption" not in non_owner_response.content
        assert b"private caption" not in unknown_response.content

    def test_edit_form_get_for_a_non_owner_returns_404_without_leaking_the_caption(
        self, client
    ) -> None:
        owner = _register_and_login(client, "formowner")
        post = _create_post(owner, caption="private caption")
        _register_and_login(client, "formintruder")

        response = client.get(_edit_url(post))

        assert response.status_code == 404
        assert b"private caption" not in response.content

    def test_edit_form_get_for_the_owner_still_renders_the_caption(self, client) -> None:
        user = _register_and_login(client, "formownerown")
        post = _create_post(user, caption="my caption")

        response = client.get(_edit_url(post))

        assert response.status_code == 200
        assert "my caption" in response.content.decode()
