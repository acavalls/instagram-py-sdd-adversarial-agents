import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

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


def _create_post(
    user: User,
    caption: str = "hello",
    media_types: tuple[str, ...] = ("image",),
) -> Post:
    media = tuple(
        PostMediaInput(file=ContentFile(b"data", name=f"media-{order}.png"), media_type=kind)
        for order, kind in enumerate(media_types)
    )
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(user=user, caption=caption, media=media)
    )
    assert output.success and output.post is not None
    return output.post


def _feed_with_followed_post(client) -> User:
    author = _register_and_login(client, "bob")
    _create_post(author)
    viewer = _register_and_login(client)
    FollowService().follow(follower=viewer, following=author)
    return viewer


@pytest.mark.django_db
class TestPostCardAnatomy:
    def test_card_header_shows_owner_avatar_and_username_link(self, client) -> None:
        _feed_with_followed_post(client)
        bob = User.objects.get(username="bob")
        profile_href = reverse("web:profile", args=[bob.pk])

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="post-avatar"' in html
        assert html.count(f'href="{profile_href}"') == 2
        assert 'data-testid="post-username"' in html
        assert ">bob</a>" in html

    def test_card_actions_row_renders_placeholders(self, client) -> None:
        _feed_with_followed_post(client)

        html = client.get(FEED_URL).content.decode()

        for testid in (
            "post-action-like",
            "post-action-comment",
            "post-action-share",
            "post-action-save",
        ):
            assert f'data-testid="{testid}"' in html
        for action in (
            "post-action-like",
            "post-action-comment",
            "post-action-share",
            "post-action-save",
        ):
            start = html.index(f'data-testid="{action}"')
            tag = html[html.rindex("<button", 0, start) : html.index("</button>", start)]
            assert "hx-" not in tag
            assert "action=" not in tag

    def test_missing_media_renders_the_placeholder_icon(self, client) -> None:
        author = _register_and_login(client, "bob")
        _create_post(author, media_types=())
        viewer = _register_and_login(client)
        FollowService().follow(follower=viewer, following=author)

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="post-media-placeholder"' in html
        assert 'data-testid="post-media-image"' not in html

    def test_multiple_media_renders_the_first_file_only(self, client) -> None:
        author = _register_and_login(client, "bob")
        _create_post(author, media_types=("image", "image"))
        viewer = _register_and_login(client)
        FollowService().follow(follower=viewer, following=author)

        html = client.get(FEED_URL).content.decode()

        assert html.count('data-testid="post-media-image"') == 1

    def test_own_post_keeps_the_edit_and_delete_menu(self, client) -> None:
        user = _register_and_login(client)
        _create_post(user)

        html = client.get(f"/web/profile/{user.pk}/").content.decode()

        assert 'data-testid="post-menu"' in html
        assert 'data-testid="post-edit-button"' in html
        assert 'data-testid="post-delete-form"' in html
        assert 'hx-get="/web/posts/' in html
        assert 'hx-post="/web/posts/' in html
