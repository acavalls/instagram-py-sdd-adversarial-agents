import uuid

import pytest
from django.core.files.base import ContentFile

from apps.accounts.models import User
from apps.posts.models import ERROR_MEDIA_LIMIT_EXCEEDED, MEDIA_LIMIT, Post, PostMedia
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import (
    ERROR_POST_DELETE_FORBIDDEN,
    ERROR_POST_EDIT_FORBIDDEN,
    ERROR_POST_NOT_FOUND,
    CreatePostInput,
    CreatePostUseCase,
    DeletePostInput,
    DeletePostUseCase,
    GetPostInput,
    GetPostUseCase,
    ListPostsInput,
    ListPostsUseCase,
    UpdatePostInput,
    UpdatePostUseCase,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _media_input(name: str = "media.png", media_type: str = "image") -> PostMediaInput:
    return PostMediaInput(file=ContentFile(b"data", name=name), media_type=media_type)


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _create(user: User, caption: str = "hello", media: tuple = ()):
    return CreatePostUseCase(PostService()).execute(
        CreatePostInput(user=user, caption=caption, media=media)
    )


def _unknown_post_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.django_db
class TestCreatePostUseCase:
    def test_successful_creation(self) -> None:
        user = _make_user()

        output = _create(user, caption="hello", media=(_media_input("a.png"),))

        assert output.success and output.error is None
        assert output.post is not None
        assert output.post.owner == user
        assert output.post.caption == "hello"
        assert output.post.media.count() == 1

    def test_creation_too_many_media_files_rejected(self) -> None:
        user = _make_user()

        output = _create(
            user, media=tuple(_media_input(f"m{i}.png") for i in range(MEDIA_LIMIT + 1))
        )

        assert not output.success
        assert output.error == ERROR_MEDIA_LIMIT_EXCEEDED
        assert Post.objects.count() == 0
        assert PostMedia.objects.count() == 0

    def test_creation_without_media_is_valid(self) -> None:
        user = _make_user()

        output = _create(user, caption="no media")

        assert output.success
        assert output.post is not None
        assert output.post.media.count() == 0


@pytest.mark.django_db
class TestListPostsUseCase:
    def test_list_returns_own_posts_newest_first(self) -> None:
        user = _make_user()
        first = _make_post(user, caption="first")
        second = _make_post(user, caption="second")

        output = ListPostsUseCase(PostService()).execute(ListPostsInput(user=user))

        assert output.success and output.error is None
        assert [item.id for item in output.posts] == [second.id, first.id]

    def test_no_cross_user_listing(self) -> None:
        alice = _make_user("alice")
        bob = _make_user("bob")
        _make_post(bob, caption="bob's post")
        own = _make_post(alice, caption="alice's post")

        output = ListPostsUseCase(PostService()).execute(ListPostsInput(user=alice))

        assert [item.id for item in output.posts] == [own.id]

    def test_pagination_window(self) -> None:
        user = _make_user()
        posts = [_make_post(user, caption=f"post {i}") for i in range(3)]
        newest_first = [item.id for item in reversed(posts)]

        output = ListPostsUseCase(PostService()).execute(
            ListPostsInput(user=user, limit=2, offset=1)
        )

        assert [item.id for item in output.posts] == newest_first[1:3]


@pytest.mark.django_db
class TestGetPostUseCase:
    def test_existing_post_is_returned_with_media(self) -> None:
        user = _make_user()
        post = _make_post(user)
        PostMedia.objects.create(
            post=post, file=ContentFile(b"data", name="x.png"), media_type="image", order=0
        )

        output = GetPostUseCase(PostService()).execute(GetPostInput(user=user, post_id=post.id))

        assert output.success and output.error is None
        assert output.post is not None
        assert output.post.id == post.id
        assert output.post.media.count() == 1

    def test_other_users_post_is_reported_as_not_found(self) -> None:
        owner = _make_user("bob")
        post = _make_post(owner)
        reader = _make_user("alice")

        output = GetPostUseCase(PostService()).execute(GetPostInput(user=reader, post_id=post.id))

        assert not output.success
        assert output.error == ERROR_POST_NOT_FOUND
        assert output.post is None

    def test_unknown_post_returns_post_not_found(self) -> None:
        user = _make_user()

        output = GetPostUseCase(PostService()).execute(
            GetPostInput(user=user, post_id=_unknown_post_id())
        )

        assert not output.success
        assert output.error == ERROR_POST_NOT_FOUND


@pytest.mark.django_db
class TestUpdatePostUseCase:
    def test_owner_updates_caption(self) -> None:
        user = _make_user()
        post = _make_post(user, caption="old")

        output = UpdatePostUseCase(PostService()).execute(
            UpdatePostInput(user=user, post_id=post.id, caption="new caption")
        )

        assert output.success and output.error is None
        assert output.post is not None
        assert output.post.caption == "new caption"

    def test_non_owner_update_rejected(self) -> None:
        owner = _make_user("alice")
        stranger = _make_user("bob")
        post = _make_post(owner, caption="old")

        output = UpdatePostUseCase(PostService()).execute(
            UpdatePostInput(user=stranger, post_id=post.id, caption="hacked")
        )

        assert not output.success
        assert output.error == ERROR_POST_EDIT_FORBIDDEN
        post.refresh_from_db()
        assert post.caption == "old"

    def test_unknown_post_returns_post_not_found(self) -> None:
        user = _make_user()

        output = UpdatePostUseCase(PostService()).execute(
            UpdatePostInput(user=user, post_id=_unknown_post_id(), caption="new caption")
        )

        assert not output.success
        assert output.error == ERROR_POST_NOT_FOUND


@pytest.mark.django_db
class TestDeletePostUseCase:
    def test_owner_deletes_post_and_media(self) -> None:
        user = _make_user()
        post = _make_post(user)
        PostMedia.objects.create(
            post=post, file=ContentFile(b"data", name="x.png"), media_type="image", order=0
        )

        output = DeletePostUseCase(PostService()).execute(
            DeletePostInput(user=user, post_id=post.id)
        )

        assert output.success and output.error is None
        assert not Post.objects.filter(pk=post.pk).exists()
        assert PostMedia.objects.count() == 0

    def test_non_owner_deletion_rejected(self) -> None:
        owner = _make_user("alice")
        stranger = _make_user("bob")
        post = _make_post(owner)

        output = DeletePostUseCase(PostService()).execute(
            DeletePostInput(user=stranger, post_id=post.id)
        )

        assert not output.success
        assert output.error == ERROR_POST_DELETE_FORBIDDEN
        assert Post.objects.filter(pk=post.pk).exists()

    def test_unknown_post_returns_post_not_found(self) -> None:
        user = _make_user()

        output = DeletePostUseCase(PostService()).execute(
            DeletePostInput(user=user, post_id=_unknown_post_id())
        )

        assert not output.success
        assert output.error == ERROR_POST_NOT_FOUND
