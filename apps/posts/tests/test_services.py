import pytest
from django.core.files.base import ContentFile

from apps.accounts.models import User
from apps.posts.models import ERROR_MEDIA_LIMIT_EXCEEDED, MEDIA_LIMIT, Post, PostMedia
from apps.posts.services import PostMediaInput, PostService


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _media_input(name: str = "media.png", media_type: str = "image") -> PostMediaInput:
    return PostMediaInput(file=ContentFile(b"data", name=name), media_type=media_type)


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


class TestPostCreation:
    @pytest.mark.django_db
    def test_successful_creation_with_media(self) -> None:
        user = _make_user()

        output = PostService().create(
            user=user,
            caption="hello",
            media=[_media_input("a.png"), _media_input("b.png")],
        )

        assert output.success and output.error is None
        assert output.post is not None
        assert output.post.owner == user
        assert output.post.caption == "hello"
        media = list(output.post.media.order_by("order"))
        assert [item.order for item in media] == [0, 1]
        assert [item.media_type for item in media] == ["image", "image"]
        assert all(
            item.file.name is not None and item.file.name.startswith("post_media/")
            for item in media
        )

    @pytest.mark.django_db
    def test_creation_without_media_is_valid(self) -> None:
        user = _make_user()

        output = PostService().create(user=user, caption="no media")

        assert output.success
        assert output.post is not None
        assert output.post.media.count() == 0

    @pytest.mark.django_db
    def test_too_many_media_files_rejected(self) -> None:
        user = _make_user()

        output = PostService().create(
            user=user,
            caption="too many",
            media=[_media_input(f"m{i}.png") for i in range(MEDIA_LIMIT + 1)],
        )

        assert not output.success
        assert output.error == ERROR_MEDIA_LIMIT_EXCEEDED
        assert Post.objects.count() == 0
        assert PostMedia.objects.count() == 0

    @pytest.mark.django_db
    def test_over_limit_caption_rejected(self) -> None:
        user = _make_user()

        output = PostService().create(user=user, caption="x" * 2201)

        assert not output.success
        assert output.error == "Caption cannot exceed 2200 characters"
        assert Post.objects.count() == 0


class TestPostQueries:
    @pytest.mark.django_db
    def test_get_by_id_returns_post_with_owner_and_media(self) -> None:
        user = _make_user()
        post = _make_post(user)
        PostMedia.objects.create(
            post=post,
            file=ContentFile(b"data", name="x.png"),
            media_type="image",
            order=0,
        )

        fetched = PostService().get_by_id(post.id)

        assert fetched is not None
        assert fetched.owner == user
        assert fetched.media.count() == 1

    @pytest.mark.django_db
    def test_get_by_id_unknown_post_returns_none(self) -> None:
        assert PostService().get_by_id("00000000-0000-0000-0000-000000000000") is None

    @pytest.mark.django_db
    def test_exists(self) -> None:
        user = _make_user()
        post = _make_post(user)
        service = PostService()

        assert service.exists(post.id)
        assert not service.exists("00000000-0000-0000-0000-000000000000")

    @pytest.mark.django_db
    def test_is_owner(self) -> None:
        owner = _make_user("alice")
        stranger = _make_user("bob")
        post = _make_post(owner)
        service = PostService()

        assert service.is_owner(owner, post)
        assert not service.is_owner(stranger, post)


class TestPostListing:
    @pytest.mark.django_db
    def test_list_returns_only_own_posts_newest_first(self) -> None:
        alice = _make_user("alice")
        bob = _make_user("bob")
        first = _make_post(alice, caption="first")
        second = _make_post(alice, caption="second")
        _make_post(bob, caption="bob's post")

        posts = PostService().list_for_user(alice)

        assert [item.id for item in posts] == [second.id, first.id]
        assert all(item.owner == alice for item in posts)

    @pytest.mark.django_db
    def test_pagination_window_limit_offset(self) -> None:
        user = _make_user()
        posts = [_make_post(user, caption=f"post {i}") for i in range(5)]
        newest_first = [item.id for item in reversed(posts)]
        service = PostService()

        window = service.list_for_user(user, limit=2, offset=1)

        assert [item.id for item in window] == newest_first[1:3]

    @pytest.mark.django_db
    def test_pagination_window_beyond_the_end_is_empty(self) -> None:
        user = _make_user()
        _make_post(user)

        window = PostService().list_for_user(user, limit=2, offset=5)

        assert window == []


class TestCaptionUpdate:
    @pytest.mark.django_db
    def test_caption_update_applies(self) -> None:
        user = _make_user()
        post = _make_post(user, caption="old")

        output = PostService().update_caption(post=post, caption="new caption")

        assert output.success and output.error is None
        assert output.post is not None
        assert output.post.caption == "new caption"
        post.refresh_from_db()
        assert post.caption == "new caption"

    @pytest.mark.django_db
    def test_caption_update_over_limit_rejected(self) -> None:
        user = _make_user()
        post = _make_post(user, caption="old")

        output = PostService().update_caption(post=post, caption="x" * 2201)

        assert not output.success
        assert output.error == "Caption cannot exceed 2200 characters"
        post.refresh_from_db()
        assert post.caption == "old"


class TestPostDeletion:
    @pytest.mark.django_db
    def test_delete_removes_post_and_its_media(self) -> None:
        user = _make_user()
        post = _make_post(user)
        PostMedia.objects.create(
            post=post, file=ContentFile(b"data", name="x.png"), media_type="image", order=0
        )
        media = post.media.first()
        assert media is not None
        media_id = media.pk

        output = PostService().delete(post=post)

        assert output.success and output.error is None
        assert not Post.objects.filter(pk=post.pk).exists()
        assert not PostMedia.objects.filter(pk=media_id).exists()
