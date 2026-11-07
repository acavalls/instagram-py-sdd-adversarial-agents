"""Model tests for the posts domain, named after the spec scenarios."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.models import F

from apps.accounts.models import User
from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    CAPTION_TOO_LONG_ERROR,
    MEDIA_MAX_COUNT,
    MEDIA_TOO_MANY_ERROR,
    POST_DELETE_NOT_OWNER_ERROR,
    POST_EDIT_NOT_OWNER_ERROR,
    MediaType,
    Post,
    PostMedia,
)

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


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


def make_media(post, order):
    """Create a media row without touching the filesystem (name-only)."""
    return PostMedia.objects.create(
        post=post,
        image=f"post_media/{post.pk}-{order}.jpg",
        media_type=MediaType.IMAGE,
        order=order,
    )


def test_post_persisted_with_media():
    """Scenario: Post persisted with media — a post with a caption and media
    files is stored with a UUID identifier, its media ordered by position and
    newest posts first in listings."""
    user = make_user()

    post = make_post(user, caption="my first post")
    first_media = make_media(post, order=0)
    second_media = make_media(post, order=1)

    # UUID identifier
    assert isinstance(post.pk, uuid.UUID)
    assert Post.objects.get(pk=post.pk) is not None

    # Caption stored as submitted; owner reachable through related_name
    stored = Post.objects.get(pk=post.pk)
    assert stored.caption == "my first post"
    assert stored.owner == user
    assert list(user.posts.all()) == [post]

    # Media attached to the post, ordered by position (zero-based)
    assert list(post.media.all()) == [first_media, second_media]
    assert [media.order for media in post.media.all()] == [0, 1]
    assert first_media.media_type == MediaType.IMAGE

    # Newest posts first in listings
    newest = make_post(user, caption="my second post")
    assert list(Post.objects.all()) == [newest, post]
    assert list(user.posts.all()) == [newest, post]

    # Timestamps are set on creation
    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_caption_length_limit():
    """Scenario: Caption length limit — a caption longer than 2200
    characters is rejected with a field-level validation error, both by
    ``full_clean()`` and by a bare ``save()``; the boundary value is valid."""
    user = make_user()

    too_long_caption = "a" * (CAPTION_MAX_LENGTH + 1)

    # full_clean reports a field-level error for "caption" (Django's
    # MaxLengthValidator wording; the spec requires a field-level error)
    post = Post(owner=user, caption=too_long_caption)
    with pytest.raises(ValidationError) as excinfo:
        post.full_clean()
    assert "caption" in excinfo.value.message_dict

    # A bare save() is rejected too (never persisted)
    with pytest.raises(ValidationError) as excinfo:
        Post(owner=user, caption=too_long_caption).save()
    assert CAPTION_TOO_LONG_ERROR in str(excinfo.value)
    assert not Post.objects.filter(owner=user).exists()

    # The boundary value (exactly 2200 characters) is accepted
    boundary_post = make_post(user, caption="b" * CAPTION_MAX_LENGTH)
    assert Post.objects.get(pk=boundary_post.pk).caption == "b" * CAPTION_MAX_LENGTH


def test_media_count_limit_rejects_the_eleventh_media():
    """Spec scenario: Post persisted with media (model-level backstop) —
    ``PostMedia.save()`` rejects attaching an 11th media file to a post with
    a field-level validation error, on every persistence path (a bare
    ``save()`` and ``objects.create``, which calls ``save()``); the boundary
    value (10 files) and updating an existing row are still allowed."""
    user = make_user()
    post = make_post(user)
    for order in range(MEDIA_MAX_COUNT):
        make_media(post, order=order)
    assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT

    # A bare save() of an 11th media row is rejected with a field-level
    # error on "post" (mirroring the caption guard pattern) and nothing is
    # persisted.
    eleventh = PostMedia(
        post=post,
        image=f"post_media/{post.pk}-10.jpg",
        media_type=MediaType.IMAGE,
        order=10,
    )
    with pytest.raises(ValidationError) as excinfo:
        eleventh.save()
    assert "post" in excinfo.value.message_dict
    assert MEDIA_TOO_MANY_ERROR in str(excinfo.value)
    assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT

    # objects.create() runs the same guard (it calls save()).
    with pytest.raises(ValidationError) as excinfo:
        PostMedia.objects.create(
            post=post,
            image=f"post_media/{post.pk}-11.jpg",
            media_type=MediaType.IMAGE,
            order=11,
        )
    assert MEDIA_TOO_MANY_ERROR in str(excinfo.value)
    assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT

    # Updating an existing row is not blocked (it does not add a file).
    first_media = PostMedia.objects.get(post=post, order=0)
    first_media.media_type = MediaType.VIDEO
    first_media.save()
    stored = PostMedia.objects.get(pk=first_media.pk)
    assert stored.media_type == MediaType.VIDEO

    # The boundary is exactly 10: after removing one file, a new one fits.
    PostMedia.objects.get(post=post, order=1).delete()
    replacement = make_media(post, order=1)
    assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT
    assert replacement.order == 1


def test_caption_length_limit_bulk_create_is_guarded():
    """Scenario: Caption length limit (bulk-create path, BUG-R005) —
    ``Post.objects.bulk_create()`` cannot persist a caption longer than 2200
    characters: an over-limit literal caption is dropped from the batch
    (pinned silent-refusal contract), a non-literal caption expression is
    refused with the model's caption ``ValidationError``, and valid captions
    (including the 2200-character boundary) are still stored."""
    user = make_user()

    # A mixed batch: one valid, one at the boundary, one over the limit.
    posts = [
        Post(owner=user, caption="fine"),
        Post(owner=user, caption="b" * CAPTION_MAX_LENGTH),
        Post(owner=user, caption="y" * (CAPTION_MAX_LENGTH + 1)),
    ]
    created = Post.objects.bulk_create(posts)
    assert len(created) == 2, "the over-limit post must not be created"
    captions = set(Post.objects.filter(owner=user).values_list("caption", flat=True))
    assert captions == {"fine", "b" * CAPTION_MAX_LENGTH}
    assert not Post.objects.filter(caption="y" * (CAPTION_MAX_LENGTH + 1)).exists()

    # A non-literal caption expression (no text to validate) is refused with
    # the model's caption ValidationError.
    expression_post = Post(owner=user)
    expression_post.caption = F("caption")
    with pytest.raises(ValidationError) as excinfo:
        Post.objects.bulk_create([expression_post])
    assert CAPTION_TOO_LONG_ERROR in str(excinfo.value)
    assert Post.objects.filter(owner=user).count() == 2


def test_ownership_rules_report_spec_errors():
    """Ownership rules on the model (design decision 2): ``can_edit`` and
    ``can_delete`` return the spec error texts for non-owners and success
    for the owner."""
    owner = make_user()
    stranger = make_user(username="bob", email="bob@example.com")
    post = make_post(owner)

    assert Post.can_edit(post, owner) == (True, None)
    assert Post.can_edit(post, stranger) == (False, POST_EDIT_NOT_OWNER_ERROR)
    assert Post.can_delete(post, owner) == (True, None)
    assert Post.can_delete(post, stranger) == (False, POST_DELETE_NOT_OWNER_ERROR)
