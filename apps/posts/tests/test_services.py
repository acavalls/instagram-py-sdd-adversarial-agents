"""Service tests for the posts domain (task 2.1)."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import MEDIA_TOO_MANY_ERROR, MediaType, Post, PostMedia
from apps.posts.services import PostService

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


def make_media_file(name="media.gif"):
    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def make_post(user, caption="hello world"):
    return Post.objects.create(owner=user, caption=caption)


def test_get_by_id_returns_post_with_owner_and_media_prefetched():
    """``get_by_id`` returns the post with owner and media loaded up front
    (design decision 3) and ``None`` for an unknown identifier."""
    user = make_user()
    post = make_post(user, caption="with media")
    PostMedia.objects.create(post=post, image=f"post_media/{post.pk}-0.jpg", order=0)

    with CaptureQueriesContext(connection) as context:
        found = PostService().get_by_id(post.pk)
    # One query for the post (owner joined) plus one for the media; nothing
    # extra when the caller touches them afterwards.
    assert len(context) <= 2
    assert found is not None
    assert found.pk == post.pk
    assert found.caption == "with media"
    assert found.owner == user  # already loaded by select_related
    assert [media.order for media in found.media.all()] == [0]  # prefetched

    unknown = PostService().get_by_id(uuid.uuid4())
    assert unknown is None


def test_list_for_user_returns_own_posts_newest_first():
    """Only the requested user's own posts are listed, newest first; other
    users' posts are never included (spec: No cross-user listing)."""
    user = make_user()
    stranger = make_user(username="bob", email="bob@example.com")

    first = make_post(user, caption="first")
    second = make_post(user, caption="second")
    make_post(stranger, caption="not mine")

    posts = PostService().list_for_user(user, limit=10, offset=0)
    assert posts == [second, first]
    assert all(post.owner == user for post in posts)


def test_list_for_user_pagination_window():
    """Spec scenario: Pagination window — limit/offset return exactly the
    requested window without duplicates across pages."""
    user = make_user()
    posts = [make_post(user, caption=f"post {index}") for index in range(5)]

    page_one = PostService().list_for_user(user, limit=2, offset=0)
    page_two = PostService().list_for_user(user, limit=2, offset=2)

    assert [post.pk for post in page_one] == [posts[4].pk, posts[3].pk]
    assert [post.pk for post in page_two] == [posts[2].pk, posts[1].pk]
    # No duplicates across pages
    assert not {post.pk for post in page_one} & {post.pk for post in page_two}


def test_list_for_user_identical_created_at_stable_window():
    """Spec scenario: Pagination window — two posts with identical
    ``created_at`` keep a stable, duplicate-free window: the ``-id``
    tiebreaker (design decision 2, same pair as ``Post.Meta.ordering``)
    makes the order deterministic across pages and queries."""
    user = make_user()
    same_time = timezone.now()
    posts = []
    for index in range(3):
        post = make_post(user, caption=f"tied {index}")
        Post.objects.filter(pk=post.pk).update(created_at=same_time)
        posts.append(Post.objects.get(pk=post.pk))

    page_one = PostService().list_for_user(user, limit=2, offset=0)
    page_two = PostService().list_for_user(user, limit=2, offset=2)

    # Every post appears exactly once across the pages (duplicate-free)
    all_pks = [post.pk for post in (*page_one, *page_two)]
    assert len(set(all_pks)) == len(all_pks) == 3
    assert {post.pk for post in (*page_one, *page_two)} == {post.pk for post in posts}
    # The window is stable: the full listing agrees with the pages' order,
    # and repeating the same query returns the same order.
    full = PostService().list_for_user(user, limit=10, offset=0)
    assert all_pks == [post.pk for post in full]
    assert [post.pk for post in PostService().list_for_user(user, limit=2, offset=0)] == [
        post.pk for post in page_one
    ]


def test_exists_reports_post_presence():
    service = PostService()
    user = make_user()
    post = make_post(user)

    assert service.exists(post.pk) is True
    assert service.exists(uuid.uuid4()) is False


def test_is_owner_true_only_for_the_owner():
    service = PostService()
    owner = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    post = make_post(owner)

    assert service.is_owner(post, owner) is True
    assert service.is_owner(post, stranger) is False


def test_create_persists_post_with_media_in_order():
    """Spec scenario: Post persisted with media (service level) — the post
    and its media are stored, media keeping the submitted order."""
    user = make_user()
    media_files = [make_media_file("one.gif"), make_media_file("two.gif")]

    post = PostService().create(user, caption="my first post", media_files=media_files)

    assert isinstance(post.pk, uuid.UUID)
    assert post.caption == "my first post"
    assert post.owner == user

    media = list(post.media.all())
    assert [item.order for item in media] == [0, 1]
    assert all(item.media_type == MediaType.IMAGE for item in media)
    # Files land under the post_media/ upload path; storage may add a
    # deduplication suffix when a file with the same name already exists
    # (media accumulate across test runs by design).
    names = [item.image.name or "" for item in media]
    assert all(name.startswith("post_media/") for name in names)
    assert len(set(names)) == 2


def test_create_without_media_is_valid():
    """Spec: Post creation — the system MUST NOT require media for a post
    to be valid."""
    user = make_user()

    post = PostService().create(user, caption="just a caption")

    assert Post.objects.get(pk=post.pk).caption == "just a caption"
    assert post.media.count() == 0


def test_create_with_too_many_media_files_persists_nothing():
    """Spec: Post creation (design decision 3, audit F-03/CS-001) —
    ``PostService.create`` persists media through ``bulk_create``, which
    bypasses ``PostMedia.save()``; the service enforces the 10-media cap
    itself and nothing is persisted when it is violated."""
    user = make_user()
    media_files = [make_media_file(f"media-{index}.gif") for index in range(11)]

    with pytest.raises(ValidationError) as excinfo:
        PostService().create(user, caption="overflow", media_files=media_files)

    assert MEDIA_TOO_MANY_ERROR in str(excinfo.value)
    # Nothing persisted: no post, no media.
    assert not Post.objects.filter(caption="overflow").exists()
    assert PostMedia.objects.count() == 0


def test_update_caption_updates_caption_and_timestamp():
    user = make_user()
    post = make_post(user, caption="before")
    previous_updated_at = post.updated_at

    updated = PostService().update_caption(post, "after")

    assert updated.caption == "after"
    stored = Post.objects.get(pk=post.pk)
    assert stored.caption == "after"
    # auto_now bumps updated_at past the previous value
    assert stored.updated_at > previous_updated_at


def test_delete_removes_post_and_cascades_media():
    user = make_user()
    post = make_post(user)
    PostMedia.objects.create(post=post, image="post_media/x.jpg", order=0)

    PostService().delete(post)

    assert not Post.objects.filter(pk=post.pk).exists()
    assert not PostMedia.objects.filter(post_id=post.pk).exists()
