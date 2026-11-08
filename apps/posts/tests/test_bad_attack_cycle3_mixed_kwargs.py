"""The Bad — cycle-3 attacks on the mixed-kwarg fix surface of PostMediaQuerySet.

The cycle 1-2 fixes route `update(post=...)` and `update(post_id=...)`
through the same capacity simulation, but a single call can carry BOTH
keywords. Django resolves both names to the same FK column and emits
`SET post_id = X, post_id = Y`; SQLite accepts the duplicate assignment
and the LAST value wins. The simulation reads only the first intercepted
key ("post"), so the capacity may be simulated against one post while the
row is actually stored in another. The spec (posts) requires the media
limit to hold on EVERY storage path, including queryset bulk operations.
"""

import pytest
from django.core.files.base import ContentFile
from django.db.models import F

from apps.accounts.models import User
from apps.posts.models import CAPTION_MAX_LENGTH, MEDIA_LIMIT, Post, PostMedia


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _media(post: Post, order: int = 0) -> PostMedia:
    media = PostMedia(post=post, media_type="image", order=order)
    media.file.save(f"attack-c3-{order}.png", ContentFile(b"data"), save=False)
    return media


def _fill(post: Post, count: int = MEDIA_LIMIT) -> list[PostMedia]:
    return list(PostMedia.objects.bulk_create(_media(post, order=i) for i in range(count)))


@pytest.mark.django_db
class TestMixedPostKwargs:
    def test_mixed_post_then_post_id_kwargs_cannot_exceed_a_full_post(self) -> None:
        """The simulation must not count capacity against one post while the
        write lands in another (duplicate SET: the last kwarg wins)."""
        owner = _make_user("mixedowner")
        full = _make_post(owner, "full")
        _fill(full)
        other = _make_post(owner, "other")
        _fill(other, 2)

        PostMedia.objects.filter(post=other).update(post=other, post_id=full.pk)

        assert PostMedia.objects.filter(post_id=full.pk).count() <= MEDIA_LIMIT

    def test_mixed_post_id_then_post_kwargs_cannot_exceed_a_full_post(self) -> None:
        """Reverse insertion order: the simulation picks the "post" key, but
        the actual stored value must still never exceed the limit."""
        owner = _make_user("mixedrev")
        full = _make_post(owner, "full")
        _fill(full)
        other = _make_post(owner, "other")
        _fill(other, 2)

        PostMedia.objects.filter(post=other).update(post_id=full.pk, post=other)

        assert PostMedia.objects.filter(post_id=full.pk).count() <= MEDIA_LIMIT

    def test_mixed_kwargs_refuse_when_the_simulated_target_is_full(self) -> None:
        """When the simulated target is full nothing may be stored, even if
        the last-wins column would point at a post with free capacity."""
        owner = _make_user("mixedrefuse")
        full = _make_post(owner, "full")
        _fill(full)
        other = _make_post(owner, "other")
        _fill(other, 2)

        rows = PostMedia.objects.filter(post=other).update(post=full, post_id=other.pk)

        assert rows == 0
        assert PostMedia.objects.filter(post_id=full.pk).count() == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=other.pk).count() == 2

    def test_bulk_update_with_both_post_and_post_id_fields_respects_the_limit(self) -> None:
        owner = _make_user("mixedbulk")
        full = _make_post(owner, "full")
        _fill(full)
        other = _make_post(owner, "other")
        moving = _fill(other, 2)[0]
        moving.post = full

        try:
            PostMedia.objects.bulk_update([moving], ["post", "post_id"])
        except Exception:
            pytest.skip("Django refuses duplicated post fields on bulk_update")

        assert PostMedia.objects.filter(post_id=full.pk).count() <= MEDIA_LIMIT


@pytest.mark.django_db
class TestAttnameAndExpressionEdges:
    def test_same_post_attname_update_still_applies_other_field_changes(self) -> None:
        owner = _make_user("attamesame")
        post = _make_post(owner)
        media = _fill(post, 3)[0]

        rows = PostMedia.objects.filter(pk=media.pk).update(post_id=post.pk, order=99)

        assert rows == 1
        media.refresh_from_db()
        assert media.order == 99
        assert PostMedia.objects.filter(post_id=post.pk).count() == 3

    def test_update_with_non_literal_post_id_refuses_silently(self) -> None:
        owner = _make_user("expratt")
        post = _make_post(owner)
        _fill(post, 2)

        rows = PostMedia.objects.filter(post=post).update(post_id=F("post_id"), order=1)

        assert rows == 0
        assert PostMedia.objects.filter(post_id=post.pk).count() == 2


@pytest.mark.django_db
class TestCapacityBoundaryOnMovePaths:
    def test_update_move_fills_target_to_exactly_ten_and_no_more(self) -> None:
        """Boundary: the move may fill a post to exactly 10 and never beyond.
        (A source post with more than 10 rows is an unreachable state: the
        bulk_create cap correctly refuses it.)"""
        owner = _make_user("boundarymove")
        target = _make_post(owner, "target")
        source = _make_post(owner, "source")
        _fill(source, MEDIA_LIMIT)

        rows = PostMedia.objects.filter(post=source).update(post=target)

        assert rows == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=target.pk).count() == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=source.pk).count() == 0

    def test_bulk_update_post_field_move_into_the_last_free_slot_applies(self) -> None:
        owner = _make_user("boundarybulk")
        target = _make_post(owner, "target")
        _fill(target, MEDIA_LIMIT - 1)
        source = _make_post(owner, "source")
        moving = _fill(source, 1)[0]
        moving.post = target

        PostMedia.objects.bulk_update([moving], ["post"])

        assert PostMedia.objects.filter(post_id=target.pk).count() == MEDIA_LIMIT


@pytest.mark.django_db
class TestCaptionBoundaryOnPostBulkPaths:
    def test_queryset_update_caption_exactly_2200_applies(self) -> None:
        owner = _make_user("capupd")
        post = _make_post(owner, "short")
        caption = "a" * CAPTION_MAX_LENGTH

        rows = Post.objects.filter(pk=post.pk).update(caption=caption)

        assert rows == 1
        post.refresh_from_db()
        assert post.caption == caption

    def test_queryset_update_caption_2201_stores_nothing(self) -> None:
        owner = _make_user("capupd2")
        post = _make_post(owner, "short")

        rows = Post.objects.filter(pk=post.pk).update(caption="a" * (CAPTION_MAX_LENGTH + 1))

        assert rows == 0
        post.refresh_from_db()
        assert post.caption == "short"

    def test_queryset_update_non_literal_caption_refuses_silently(self) -> None:
        owner = _make_user("capexpr")
        post = _make_post(owner, "short")

        rows = Post.objects.filter(pk=post.pk).update(caption=F("caption"))

        assert rows == 0
        post.refresh_from_db()
        assert post.caption == "short"

    def test_post_bulk_update_caption_exactly_2200_applies(self) -> None:
        owner = _make_user("capbulk")
        post = _make_post(owner, "short")
        post.caption = "a" * CAPTION_MAX_LENGTH

        Post.objects.bulk_update([post], ["caption"])

        post.refresh_from_db()
        assert post.caption == "a" * CAPTION_MAX_LENGTH

    def test_post_bulk_create_caption_exactly_2200_is_kept(self) -> None:
        owner = _make_user("capcreate")

        created = list(
            Post.objects.bulk_create([Post(owner=owner, caption="a" * CAPTION_MAX_LENGTH)])
        )

        assert len(created) == 1
        assert created[0].caption == "a" * CAPTION_MAX_LENGTH

    def test_post_bulk_create_caption_2201_is_refused_without_raising(self) -> None:
        owner = _make_user("capcreate2")

        created = list(
            Post.objects.bulk_create([Post(owner=owner, caption="a" * (CAPTION_MAX_LENGTH + 1))])
        )

        assert len(created) == 0
        assert Post.objects.filter(owner=owner).count() == 0
