"""Model tests for the posts domain, named after the spec scenarios."""

import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    CAPTION_TOO_LONG_ERROR,
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
