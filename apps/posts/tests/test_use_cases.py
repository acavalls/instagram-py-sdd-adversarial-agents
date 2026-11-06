"""Use case tests for the posts domain (task 2.2), named after the spec
scenarios they back at the use case level."""

import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.posts.models import POST_DELETE_NOT_OWNER_ERROR, POST_EDIT_NOT_OWNER_ERROR, Post
from apps.posts.use_cases import (
    POST_NOT_FOUND_ERROR,
    CreatePostInput,
    CreatePostUseCase,
    DeletePostInput,
    DeletePostUseCase,
    GetPostInput,
    GetPostUseCase,
    ListPostsInput,
    ListPostsOutput,
    ListPostsUseCase,
    UpdatePostInput,
    UpdatePostUseCase,
)

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"

# Minimal valid 1x1 transparent GIF, used as uploaded media content.
GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_post(user, caption="hello world"):
    return Post.objects.create(owner=user, caption=caption)


def make_media_file(name="media.gif"):
    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def test_create_post_success():
    output = CreatePostUseCase().execute(
        CreatePostInput(
            owner=make_user(),
            caption="my first post",
            media_files=[make_media_file()],
        )
    )
    assert output.success is True
    assert output.error is None
    assert output.post is not None
    assert output.post.caption == "my first post"
    assert output.post.media.count() == 1
    first_media = output.post.media.first()
    assert first_media is not None
    assert first_media.order == 0


def test_create_post_with_too_long_caption_rejected():
    """The use case surfaces the caption limit (models enforce it on save)."""
    output = CreatePostUseCase().execute(CreatePostInput(owner=make_user(), caption="a" * 2201))
    assert output.success is False
    assert output.post is None
    assert output.error is not None


def test_list_posts_returns_own_posts_newest_first_paginated():
    """Spec scenarios: API list of own posts + Pagination window (use case
    level): only the user's own posts, newest first, in the requested window."""
    user = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    first = make_post(user, caption="first")
    second = make_post(user, caption="second")
    make_post(stranger, caption="not mine")

    output = ListPostsUseCase().execute(ListPostsInput(user=user, limit=1, offset=0))

    assert isinstance(output, ListPostsOutput)
    assert output.success is True
    assert [post.pk for post in output.posts] == [second.pk]

    next_page = ListPostsUseCase().execute(ListPostsInput(user=user, limit=1, offset=1))
    assert [post.pk for post in next_page.posts] == [first.pk]


def test_existing_post_detail():
    """Spec scenario: Existing post detail (use case level) — the owner
    retrieves an existing post with owner and media loaded."""
    user = make_user()
    post = make_post(user, caption="look at this")

    output = GetPostUseCase().execute(GetPostInput(post_id=post.pk, user=user))

    assert output.success is True
    assert output.error is None
    assert output.post is not None
    assert output.post.pk == post.pk
    assert output.post.caption == "look at this"


def test_non_owner_detail_reports_not_found():
    """Spec requirement: Post visibility — a non-owner must not read another
    user's post; they get the same "Post not found" error as an unknown id."""
    owner = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    post = make_post(owner, caption="alice private")

    output = GetPostUseCase().execute(GetPostInput(post_id=post.pk, user=stranger))

    assert output.success is False
    assert output.error == POST_NOT_FOUND_ERROR == "Post not found"
    assert output.post is None


def test_unknown_post_detail():
    """Spec scenario: Unknown post detail — an unknown identifier reports
    exactly "Post not found"."""
    output = GetPostUseCase().execute(GetPostInput(post_id=uuid.uuid4(), user=make_user()))

    assert output.success is False
    assert output.error == POST_NOT_FOUND_ERROR == "Post not found"
    assert output.post is None


def test_list_posts_clamps_unbounded_limit_and_offset():
    """Pagination hardening: limit/offset beyond the database's integer range
    are clamped to an empty window instead of raising a database error."""
    user = make_user()
    make_post(user, caption="first")

    output = ListPostsUseCase().execute(
        ListPostsInput(user=user, limit=99999999999999999999, offset=99999999999999999999)
    )

    assert output.success is True
    assert output.posts == []


def test_owner_updates_caption_via_api():
    """Spec scenario: Owner updates caption via API (use case level) — the
    owner's update succeeds and persists the new caption."""
    owner = make_user()
    post = make_post(owner, caption="before")

    output = UpdatePostUseCase().execute(
        UpdatePostInput(post_id=post.pk, user=owner, caption="after")
    )

    assert output.success is True
    assert output.error is None
    assert output.post is not None
    assert output.post.caption == "after"
    assert Post.objects.get(pk=post.pk).caption == "after"


def test_non_owner_update_rejected():
    """Spec scenario: Non-owner update rejected — a non-owner gets the model's
    edit ownership error and the caption is unchanged."""
    owner = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    post = make_post(owner, caption="before")

    output = UpdatePostUseCase().execute(
        UpdatePostInput(post_id=post.pk, user=stranger, caption="hacked")
    )

    assert output.success is False
    assert output.error == POST_EDIT_NOT_OWNER_ERROR == "You can only edit your own posts"
    assert output.post is None
    assert Post.objects.get(pk=post.pk).caption == "before"


def test_update_unknown_post_reports_not_found():
    output = UpdatePostUseCase().execute(
        UpdatePostInput(post_id=uuid.uuid4(), user=make_user(), caption="whatever")
    )
    assert output.success is False
    assert output.error == POST_NOT_FOUND_ERROR


def test_owner_deletes_post_via_api():
    """Spec scenario: Owner deletes post via API (use case level) — the
    owner's deletion succeeds and the post is gone."""
    owner = make_user()
    post = make_post(owner)

    output = DeletePostUseCase().execute(DeletePostInput(post_id=post.pk, user=owner))

    assert output.success is True
    assert output.error is None
    assert not Post.objects.filter(pk=post.pk).exists()


def test_non_owner_deletion_rejected():
    """Spec scenario: Non-owner deletion rejected — a non-owner gets the
    model's delete ownership error and the post still exists."""
    owner = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    post = make_post(owner)

    output = DeletePostUseCase().execute(DeletePostInput(post_id=post.pk, user=stranger))

    assert output.success is False
    assert output.error == POST_DELETE_NOT_OWNER_ERROR == "You can only delete your own posts"
    assert Post.objects.filter(pk=post.pk).exists()


def test_delete_unknown_post_reports_not_found():
    output = DeletePostUseCase().execute(DeletePostInput(post_id=uuid.uuid4(), user=make_user()))
    assert output.success is False
    assert output.error == POST_NOT_FOUND_ERROR
