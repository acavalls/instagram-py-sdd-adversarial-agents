"""The Bad — attack tests for the bulk-write machinery and limit enforcement."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import F

from apps.accounts.models import User
from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    ERROR_MEDIA_LIMIT_EXCEEDED,
    MEDIA_LIMIT,
    Post,
    PostMedia,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _media(post: Post, order: int = 0, name: str = "media.png") -> PostMedia:
    media = PostMedia(post=post, media_type="image", order=order)
    media.file.save(name, ContentFile(b"data"), save=False)
    return media


def _fill(post: Post, count: int = MEDIA_LIMIT) -> list[PostMedia]:
    return list(PostMedia.objects.bulk_create(_media(post, order=i) for i in range(count)))


class TestInstanceSaveMediaMove:
    @pytest.mark.django_db
    def test_moving_media_into_a_full_post_via_instance_save_is_refused(self) -> None:
        owner = _make_user()
        full = _make_post(owner, "full")
        other = _make_post(owner, "other")
        _fill(full)
        single = _fill(other, 1)[0]

        single.post = full
        with pytest.raises(ValidationError, match=ERROR_MEDIA_LIMIT_EXCEEDED):
            single.save()

        assert PostMedia.objects.filter(post_id=full.pk).count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_moving_media_into_a_post_with_one_free_slot_via_instance_save_applies(
        self,
    ) -> None:
        owner = _make_user()
        full = _make_post(owner, "full")
        other = _make_post(owner, "other")
        _fill(full)
        single = _fill(other, 1)[0]
        PostMedia.objects.filter(post=full).first().delete()

        single.post = full
        single.save()

        assert PostMedia.objects.filter(post_id=full.pk).count() == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=other.pk).count() == 0


class TestGateHygiene:
    @pytest.mark.django_db
    def test_gate_does_not_leak_after_a_refused_bulk_write(self) -> None:
        owner = _make_user()
        post = _make_post(owner, "original")

        with pytest.raises(ValidationError):
            Post.objects.bulk_create([Post(owner=owner, caption=F("caption"))])
        with pytest.raises(ValidationError):
            post.caption = F("caption")
            Post.objects.bulk_update([post], ["caption"])

        assert Post.objects.update(caption="x" * (CAPTION_MAX_LENGTH + 1)) == 0
        refreshed = Post.objects.get(pk=post.pk)
        assert refreshed.caption == "original"
        assert Post.objects.update(caption="changed") == 1


class TestMixedBatches:
    @pytest.mark.django_db
    def test_post_bulk_create_mixed_batch_stores_only_compliant_rows(self) -> None:
        owner = _make_user()

        Post.objects.bulk_create(
            [
                Post(owner=owner, caption="one"),
                Post(owner=owner, caption="x" * (CAPTION_MAX_LENGTH + 1)),
                Post(owner=owner, caption="two"),
            ]
        )

        captions = set(Post.objects.filter(owner=owner).values_list("caption", flat=True))
        assert captions == {"one", "two"}

    @pytest.mark.django_db
    def test_media_bulk_create_on_full_post_stores_nothing(self) -> None:
        owner = _make_user()
        post = _make_post(owner)
        _fill(post)

        PostMedia.objects.bulk_create([_media(post, order=99)])

        assert PostMedia.objects.filter(post_id=post.pk).count() == MEDIA_LIMIT


class TestMediaMoves:
    @pytest.mark.django_db
    def test_media_bulk_update_simultaneous_swap_keeps_both_limits(self) -> None:
        owner = _make_user()
        full = _make_post(owner, "full")
        other = _make_post(owner, "other")
        full_media = _fill(full)
        other_media = _fill(other, 2)

        moving_out = full_media[0]
        moving_in = other_media[0]
        moving_out.post = other
        moving_in.post = full
        PostMedia.objects.bulk_update([moving_out, moving_in], ["post"])

        assert PostMedia.objects.filter(post_id=full.pk).count() == MEDIA_LIMIT
        assert PostMedia.objects.filter(post_id=other.pk).count() == 2

    @pytest.mark.django_db
    def test_update_post_on_sliced_queryset_is_refused_like_native_django(self) -> None:
        owner = _make_user()
        source = _make_post(owner, "source")
        target = _make_post(owner, "target")
        _fill(source)
        _fill(target, 5)

        queryset = PostMedia.objects.filter(post=source).order_by("order")[:3]
        with pytest.raises(TypeError):
            queryset.update(post=target)

        assert PostMedia.objects.filter(post_id=target.pk).count() == 5
        assert PostMedia.objects.filter(post_id=source.pk).count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_media_bulk_update_order_fields_only_applies(self) -> None:
        owner = _make_user()
        post = _make_post(owner)
        medias = _fill(post, 3)
        medias[0].order = 5
        medias[1].order = 6

        PostMedia.objects.bulk_update(medias[:2], ["order"])

        orders = sorted(PostMedia.objects.filter(post=post).values_list("order", flat=True))
        assert orders == [2, 5, 6]
