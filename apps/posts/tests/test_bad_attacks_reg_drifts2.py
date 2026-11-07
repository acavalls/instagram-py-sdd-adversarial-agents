"""The Bad — attack iteration 2 on change ``regularize-social-drifts``.

Posts domain: re-verification of BUG-R001 with different angles (related
manager ``post.media.bulk_create``, mixed per-post capacity in one call)
plus fresh ``bulk_update``/``update`` reassignment and caption attacks not
covered in iteration 1.
"""

from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.posts.models import MEDIA_MAX_COUNT, Post, PostMedia

pytestmark = pytest.mark.django_db

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def make_user(**overrides: Any) -> User:
    data = {"username": "alice", "email": "alice@example.com", "password": "sup3r-secret-pw"}
    data.update(overrides)
    return User.objects.create_user(**data)


def make_media_file(name: str = "media.gif"):
    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def fill_post(post: Post, count: int) -> None:
    PostMedia.objects.bulk_create(
        [
            PostMedia(post=post, image=make_media_file(f"{post.pk}-{i}.gif"), order=i)
            for i in range(count)
        ]
    )


class TestR001Reattack:
    def test_atk_r019_related_manager_bulk_create_respects_per_post_cap(self):
        """BUG-R001 re-check, new angle: the related manager
        ``post.media.bulk_create`` must go through PostMediaQuerySet
        (Manager.from_queryset idiom) and cap at 10 total for the post."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="rel")
        fill_post(post, 3)
        files = [
            PostMedia(post=post, image=make_media_file(f"r{i}.gif"), order=100 + i)
            for i in range(11)
        ]
        post.media.bulk_create(files)
        assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT, (
            "related-manager bulk_create stored beyond 10 media"
        )

    def test_atk_r020_mixed_capacity_two_posts_single_call(self):
        """BUG-R001 re-check, new angle: one bulk_create call mixing two
        posts with different remaining capacity must cap EACH post
        independently (per-post accounting, not per-call)."""
        user = make_user()
        post_a = Post.objects.create(owner=user, caption="a")  # 9 existing -> room for 1
        post_b = Post.objects.create(owner=user, caption="b")  # 0 existing -> room for 10
        fill_post(post_a, 9)
        files = [
            PostMedia(post=post_a, image=make_media_file(f"a{i}.gif"), order=50 + i)
            for i in range(3)
        ] + [PostMedia(post=post_b, image=make_media_file(f"b{i}.gif"), order=i) for i in range(5)]
        PostMedia.objects.bulk_create(files)
        assert PostMedia.objects.filter(post=post_a).count() == MEDIA_MAX_COUNT, (
            "post A exceeded 10"
        )
        assert PostMedia.objects.filter(post=post_b).count() == 5, "post B lost valid rows"


class TestFreshReassignmentAndCaptionAttacks:
    def test_atk_r021_bulk_update_reassign_post_exceeds_media_cap(self):
        """Fresh attack: ``bulk_update`` is a queryset bulk storage path that
        skips ``PostMedia.save()``. Re-pointing a media row from a post with
        room to a FULL post (order=99 dodges the (post, order) unique
        constraint so the count is the only thing under test) must not push
        the target post beyond 10 attached files. Delta (posts, Post data
        model): 'The system SHALL store post media as up to 10 ordered files
        attached to a post.'"""
        user = make_user()
        full = Post.objects.create(owner=user, caption="full")
        other = Post.objects.create(owner=user, caption="other")
        fill_post(full, MEDIA_MAX_COUNT)
        stray = PostMedia(post=other, image=make_media_file("stray.gif"), order=99)
        stray.save()
        stray.post = full
        PostMedia.objects.bulk_update([stray], ["post"])
        assert PostMedia.objects.filter(post=full).count() == MEDIA_MAX_COUNT, (
            f"bulk_update reassignment stored an 11th media on the full post "
            f"({PostMedia.objects.filter(post=full).count()})"
        )

    def test_atk_r022_queryset_update_reassign_post_exceeds_media_cap(self):
        """Fresh attack: ``PostMedia.objects.update(post=...)`` is a bulk
        storage path with no override on PostMediaQuerySet; reassigning a
        media row onto a full post must not push it beyond 10 files."""
        user = make_user()
        full = Post.objects.create(owner=user, caption="full")
        other = Post.objects.create(owner=user, caption="other")
        fill_post(full, MEDIA_MAX_COUNT)
        stray = PostMedia(post=other, image=make_media_file("stray2.gif"), order=99)
        stray.save()
        PostMedia.objects.filter(pk=stray.pk).update(post=full)
        assert PostMedia.objects.filter(post=full).count() == MEDIA_MAX_COUNT, (
            f"queryset update reassignment stored an 11th media on the full "
            f"post ({PostMedia.objects.filter(post=full).count()})"
        )

    def test_atk_r023_post_queryset_update_caption_over_limit(self):
        """Fresh attack: ``Post.objects.update(caption=...)`` is a bulk
        update path with no override; the delta (posts, Post data model)
        requires 'a caption of at most 2200 characters' and the Caption
        length limit scenario says an update with a longer caption is
        rejected. A 3000-character caption must never be stored."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="ok")
        Post.objects.filter(pk=post.pk).update(caption="x" * 3000)
        post.refresh_from_db()
        assert len(post.caption) <= 2200, (
            f"queryset update stored a {len(post.caption)}-character caption"
        )
