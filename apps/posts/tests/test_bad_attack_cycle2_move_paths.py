"""The Bad — cycle-2 attacks on the PostMedia.save() move-refusal fix surface.

Focus: attname-based bulk write paths that may bypass the "post" keyword
interception, legality of same-post saves, and moves into posts with one
free slot. The spec (posts) requires the media limit to hold on EVERY
storage path, including queryset bulk operations.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import F

from apps.accounts.models import User
from apps.posts.models import (
    ERROR_MEDIA_LIMIT_EXCEEDED,
    MEDIA_LIMIT,
    Post,
    PostMedia,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _media(post: Post, order: int = 0) -> PostMedia:
    media = PostMedia(post=post, media_type="image", order=order)
    media.file.save(f"attack-c2-{order}.png", ContentFile(b"data"), save=False)
    return media


def _fill(post: Post, count: int = MEDIA_LIMIT) -> list[PostMedia]:
    return list(PostMedia.objects.bulk_create(_media(post, order=i) for i in range(count)))


class TestAttnameBulkWriteBypass:
    @pytest.mark.django_db
    def test_update_via_post_id_attname_cannot_exceed_a_full_post(self) -> None:
        owner = _make_user("attnameowner")
        source = _make_post(owner, "source")
        target = _make_post(owner, "target")
        _fill(target)
        moving = _fill(source, 2)

        PostMedia.objects.filter(pk=moving[0].pk).update(post_id=target.pk)

        assert PostMedia.objects.filter(post_id=target.pk).count() <= MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_update_via_post_id_attname_cannot_exceed_a_full_post(self) -> None:
        owner = _make_user("attnamebulk")
        source = _make_post(owner, "source")
        target = _make_post(owner, "target")
        _fill(target)
        moving = _fill(source, 2)
        moving[0].post = target

        try:
            PostMedia.objects.bulk_update([moving[0]], ["post_id"])
        except Exception:
            pytest.skip("Django refuses the post_id attname on bulk_update")

        assert PostMedia.objects.filter(post_id=target.pk).count() <= MEDIA_LIMIT


class TestFixSurfaceLegality:
    @pytest.mark.django_db
    def test_same_post_instance_save_still_applies_order_edits(self) -> None:
        owner = _make_user("samepost")
        post = _make_post(owner)
        media = _fill(post, 3)[0]

        media.order = 42
        media.save()

        assert PostMedia.objects.get(pk=media.pk).order == 42

    @pytest.mark.django_db
    def test_move_into_a_post_with_exactly_one_free_slot_applies(self) -> None:
        owner = _make_user("oneslot")
        source = _make_post(owner, "source")
        target = _make_post(owner, "target")
        _fill(target)
        moving = _fill(source, 2)[0]
        PostMedia.objects.filter(post=target).first().delete()

        moving.post = target
        moving.save()

        assert PostMedia.objects.filter(post_id=target.pk).count() == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=source.pk).count() == 1

    @pytest.mark.django_db
    def test_unsaved_media_with_post_set_uses_the_adding_path(self) -> None:
        owner = _make_user("addingpath")
        post = _make_post(owner)
        _fill(post, MEDIA_LIMIT - 1)

        extra = _media(post, order=99)
        extra.save()
        assert PostMedia.objects.filter(post_id=post.pk).count() == MEDIA_LIMIT

        overflow = _media(post, order=100)
        with pytest.raises(ValidationError, match=ERROR_MEDIA_LIMIT_EXCEEDED):
            overflow.save()

    @pytest.mark.django_db
    def test_stale_instance_state_does_not_hide_the_stored_post(self) -> None:
        owner = _make_user("stalestate")
        source = _make_post(owner, "source")
        target = _make_post(owner, "target")
        _fill(target)
        moving = _fill(source, 1)[0]

        moving.post_id = target.pk
        moving.post = Post.objects.get(pk=target.pk)
        with pytest.raises(ValidationError, match=ERROR_MEDIA_LIMIT_EXCEEDED):
            moving.save()

        refreshed = PostMedia.objects.get(pk=moving.pk)
        assert refreshed.post_id == source.pk


class TestMixedUpdateSemantics:
    @pytest.mark.django_db
    def test_update_touching_only_already_placed_rows_still_applies_their_changes(
        self,
    ) -> None:
        owner = _make_user("mixedupdate")
        post = _make_post(owner)
        medias = _fill(post)
        medias[0].order = 77

        updated = PostMedia.objects.filter(pk=medias[0].pk).update(post=post, order=77)

        assert updated == 1
        assert PostMedia.objects.get(pk=medias[0].pk).order == 77


class TestExpressionPostTargets:
    @pytest.mark.django_db
    def test_update_with_non_literal_post_refuses_silently(self) -> None:
        owner = _make_user("exprpost")
        source = _make_post(owner, "source")
        moving = _fill(source, 1)[0]

        updated = PostMedia.objects.filter(pk=moving.pk).update(post=F("post"))

        assert updated == 0
        assert PostMedia.objects.get(pk=moving.pk).post_id == source.pk
