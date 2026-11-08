import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import F, Value

from apps.accounts.models import User
from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    ERROR_CAPTION_NOT_TEXT,
    ERROR_CAPTION_TOO_LONG,
    ERROR_MEDIA_LIMIT_EXCEEDED,
    ERROR_MEDIA_POST_REQUIRED,
    MEDIA_LIMIT,
    Post,
    PostMedia,
    validate_caption,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_post(owner: User, caption: str = "hello") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _media(post: Post, order: int = 0, media_type: str = "image", name: str = "media.png"):
    media = PostMedia(post=post, media_type=media_type, order=order)
    media.file.save(name, ContentFile(b"data"), save=False)
    return media


class TestCaptionValidation:
    @pytest.mark.parametrize(
        ("caption", "expected_message"),
        [
            ("x" * (CAPTION_MAX_LENGTH + 1), ERROR_CAPTION_TOO_LONG),
            (None, ERROR_CAPTION_NOT_TEXT),
            (F("caption"), ERROR_CAPTION_NOT_TEXT),
        ],
    )
    def test_caption_validation(self, caption, expected_message: str) -> None:
        with pytest.raises(ValidationError, match=expected_message):
            validate_caption(caption)


class TestPostPersistedWithMedia:
    @pytest.mark.django_db
    def test_post_persisted_with_media(self) -> None:
        user = _make_user()
        post = _make_post(user, caption="hello")
        PostMedia.objects.bulk_create(
            [
                _media(post, order=0, name="a.png"),
                _media(post, order=1, media_type="video", name="b.mp4"),
            ]
        )

        stored = Post.objects.get(pk=post.pk)

        assert isinstance(stored.id, uuid.UUID)
        assert stored.owner == user
        assert stored.caption == "hello"
        media = list(stored.media.order_by("order"))
        assert [item.order for item in media] == [0, 1]
        assert [item.media_type for item in media] == ["image", "video"]
        assert media[0].file.name.startswith("post_media/")

    @pytest.mark.django_db
    def test_posts_are_listed_newest_first_with_deterministic_order(self) -> None:
        user = _make_user()
        first = _make_post(user, caption="first")
        second = _make_post(user, caption="second")

        ids = list(Post.objects.filter(owner=user).values_list("id", flat=True))

        assert ids == [second.id, first.id]

    @pytest.mark.django_db
    def test_post_without_caption_is_valid(self) -> None:
        user = _make_user()

        post = Post.objects.create(owner=user)

        assert post.caption == ""


class TestCaptionLengthLimit:
    @pytest.mark.django_db
    def test_caption_length_limit_on_save(self) -> None:
        user = _make_user()
        post = Post(owner=user, caption="x" * (CAPTION_MAX_LENGTH + 1))

        with pytest.raises(ValidationError, match=ERROR_CAPTION_TOO_LONG):
            post.save()

        assert not Post.objects.exists()

    @pytest.mark.django_db
    def test_caption_length_limit_is_a_field_level_error(self) -> None:
        user = _make_user()
        post = Post(owner=user, caption="x" * (CAPTION_MAX_LENGTH + 1))

        with pytest.raises(ValidationError) as excinfo:
            post.full_clean()

        assert str(excinfo.value.message_dict["caption"][0]) == ERROR_CAPTION_TOO_LONG


class TestBulkPathsRefuseOverLimitCaptions:
    @pytest.mark.django_db
    def test_bulk_paths_refuse_over_limit_captions_update(self) -> None:
        post = _make_post(_make_user(), caption="hello")

        updated = Post.objects.filter(pk=post.pk).update(caption="x" * (CAPTION_MAX_LENGTH + 1))

        assert updated == 0
        post.refresh_from_db()
        assert post.caption == "hello"

    @pytest.mark.django_db
    def test_bulk_paths_refuse_over_limit_captions_bulk_create(self) -> None:
        user = _make_user()
        over_limit = Post(owner=user, caption="x" * (CAPTION_MAX_LENGTH + 1))
        compliant = Post(owner=user, caption="fine")

        created = Post.objects.bulk_create([over_limit, compliant])

        assert [post.caption for post in created] == ["fine"]
        assert Post.objects.count() == 1
        assert Post.objects.filter(caption="fine").exists()

    @pytest.mark.django_db
    def test_bulk_paths_refuse_over_limit_captions_bulk_update(self) -> None:
        user = _make_user()
        post = _make_post(user, caption="hello")
        other = _make_post(user, caption="world")
        post.caption = "x" * (CAPTION_MAX_LENGTH + 1)
        other.caption = "new caption"

        updated = Post.objects.bulk_update([post, other], ["caption"])

        assert updated == 1
        post.refresh_from_db()
        other.refresh_from_db()
        assert post.caption == "hello"
        assert other.caption == "new caption"


class TestNonLiteralCaptionWriteRefused:
    @pytest.mark.django_db
    def test_non_literal_caption_write_refused_bulk_create(self) -> None:
        user = _make_user()
        ghost = Post(owner=user)
        ghost.caption = F("caption")  # type: ignore[assignment]

        with pytest.raises(ValidationError, match=ERROR_CAPTION_NOT_TEXT):
            Post.objects.bulk_create([ghost])

        assert not Post.objects.exists()

    @pytest.mark.django_db
    def test_non_literal_caption_write_refused_bulk_create_value_expression(self) -> None:
        user = _make_user()
        ghost = Post(owner=user)
        ghost.caption = Value("new")  # type: ignore[assignment]

        with pytest.raises(ValidationError, match=ERROR_CAPTION_NOT_TEXT):
            Post.objects.bulk_create([ghost])

        assert not Post.objects.exists()

    @pytest.mark.django_db
    def test_non_literal_caption_write_refused_bulk_update(self) -> None:
        post = _make_post(_make_user(), caption="hello")
        post.caption = F("caption")  # type: ignore[assignment]

        with pytest.raises(ValidationError, match=ERROR_CAPTION_NOT_TEXT):
            Post.objects.bulk_update([post], ["caption"])

        post.refresh_from_db()
        assert post.caption == "hello"


class TestNonLiteralCaptionUpdateRefusesSilently:
    @pytest.mark.django_db
    def test_non_literal_caption_update_refuses_silently(self) -> None:
        post = _make_post(_make_user(), caption="hello")

        assert Post.objects.filter(pk=post.pk).update(caption=F("caption")) == 0
        assert Post.objects.filter(pk=post.pk).update(caption=Value("new")) == 0

        post.refresh_from_db()
        assert post.caption == "hello"


class TestLegalCaptionBulkUpdateApplies:
    @pytest.mark.django_db
    def test_legal_caption_bulk_update_applies_update(self) -> None:
        post = _make_post(_make_user(), caption="hello")

        updated = Post.objects.filter(pk=post.pk).update(caption="new caption")

        assert updated == 1
        post.refresh_from_db()
        assert post.caption == "new caption"

    @pytest.mark.django_db
    def test_legal_caption_bulk_update_applies_bulk_update(self) -> None:
        user = _make_user()
        first = _make_post(user, caption="first")
        second = _make_post(user, caption="second")
        first.caption = "first updated"
        second.caption = "second updated"

        updated = Post.objects.bulk_update([first, second], ["caption"])

        assert updated == 2
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.caption == "first updated"
        assert second.caption == "second updated"

    @pytest.mark.django_db
    def test_legal_caption_bulk_update_applies_bulk_create(self) -> None:
        user = _make_user()

        created = Post.objects.bulk_create(
            [Post(owner=user, caption="one"), Post(owner=user, caption="two")]
        )

        assert len(created) == 2
        assert Post.objects.count() == 2


class TestBulkPathsKeepTheMediaLimit:
    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_create(self) -> None:
        post = _make_post(_make_user())
        PostMedia.objects.bulk_create(
            [_media(post, order=index, name=f"m{index}.png") for index in range(MEDIA_LIMIT)]
        )

        created = PostMedia.objects.bulk_create(
            [_media(post, order=10 + index, name=f"extra{index}.png") for index in range(3)]
        )

        assert created == []
        assert post.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_create_across_posts(self) -> None:
        user = _make_user()
        full = _make_post(user)
        other = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(full, order=index, name=f"f{index}.png") for index in range(MEDIA_LIMIT)]
        )

        created = PostMedia.objects.bulk_create(
            [_media(full, order=99, name="over.png"), _media(other, order=0, name="ok.png")]
        )

        assert [item.post for item in created] == [other]
        assert full.media.count() == MEDIA_LIMIT
        assert other.media.count() == 1

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_update(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(source, order=index, name=f"s{index}.png") for index in range(MEDIA_LIMIT)]
        )
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT)]
        )

        updated = PostMedia.objects.filter(post=source).update(post=target)

        assert updated == 0
        assert source.media.count() == MEDIA_LIMIT
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_update_applies_rows_that_fit(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(source, order=index, name=f"s{index}.png") for index in range(MEDIA_LIMIT)]
        )
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT - 1)]
        )

        updated = PostMedia.objects.filter(post=source).update(post=target)

        assert updated == 1
        assert source.media.count() == MEDIA_LIMIT - 1
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_update_refuses_non_literal_silently(self) -> None:
        user = _make_user()
        source = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(source, order=index, name=f"s{index}.png") for index in range(3)]
        )

        updated = PostMedia.objects.filter(post=source).update(post=F("post"))

        assert updated == 0
        assert source.media.count() == 3

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_update(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        source_rows = [
            PostMedia.objects.create(post=source, media_type="image", order=index)
            for index in range(MEDIA_LIMIT)
        ]
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT)]
        )

        mover = source_rows[0]
        mover.post = target
        updated = PostMedia.objects.bulk_update([mover], ["post"])

        assert updated == 0
        mover.refresh_from_db()
        assert mover.post == source
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_update_applies_rows_that_fit(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        source_rows = [
            PostMedia.objects.create(post=source, media_type="image", order=index)
            for index in range(MEDIA_LIMIT)
        ]
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT - 1)]
        )

        mover = source_rows[0]
        mover.post = target
        updated = PostMedia.objects.bulk_update([mover], ["post"])

        assert updated == 1
        mover.refresh_from_db()
        assert mover.post == target
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_update_post_id_attname(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(source, order=index, name=f"s{index}.png") for index in range(MEDIA_LIMIT)]
        )
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT)]
        )

        updated = PostMedia.objects.filter(post=source).update(post_id=target.pk)

        assert updated == 0
        assert source.media.count() == MEDIA_LIMIT
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_update_post_id_attname_applies_rows_that_fit(
        self,
    ) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        PostMedia.objects.bulk_create(
            [_media(source, order=index, name=f"s{index}.png") for index in range(MEDIA_LIMIT)]
        )
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT - 1)]
        )

        updated = PostMedia.objects.filter(post=source).update(post_id=target.pk)

        assert updated == 1
        assert source.media.count() == MEDIA_LIMIT - 1
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_update_post_id_attname(self) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        source_rows = [
            PostMedia.objects.create(post=source, media_type="image", order=index)
            for index in range(MEDIA_LIMIT)
        ]
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT)]
        )

        mover = source_rows[0]
        mover.post = target
        updated = PostMedia.objects.bulk_update([mover], ["post_id"])

        assert updated == 0
        mover.refresh_from_db()
        assert mover.post == source
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_bulk_paths_keep_the_media_limit_bulk_update_post_id_attname_applies_rows_that_fit(
        self,
    ) -> None:
        user = _make_user()
        source = _make_post(user)
        target = _make_post(user)
        source_rows = [
            PostMedia.objects.create(post=source, media_type="image", order=index)
            for index in range(MEDIA_LIMIT)
        ]
        PostMedia.objects.bulk_create(
            [_media(target, order=index, name=f"t{index}.png") for index in range(MEDIA_LIMIT - 1)]
        )

        mover = source_rows[0]
        mover.post = target
        updated = PostMedia.objects.bulk_update([mover], ["post_id"])

        assert updated == 1
        mover.refresh_from_db()
        assert mover.post == target
        assert target.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_media_limit_instance_save_refuses_when_post_is_full(self) -> None:
        post = _make_post(_make_user())
        PostMedia.objects.bulk_create(
            [_media(post, order=index, name=f"m{index}.png") for index in range(MEDIA_LIMIT)]
        )

        overflow = _media(post, order=MEDIA_LIMIT, name="overflow.png")

        with pytest.raises(ValidationError, match=ERROR_MEDIA_LIMIT_EXCEEDED):
            overflow.save()

        assert post.media.count() == MEDIA_LIMIT

    @pytest.mark.django_db
    def test_media_instance_save_applies_under_the_limit(self) -> None:
        post = _make_post(_make_user())

        media = _media(post, order=0, name="single.png")
        media.save()

        assert post.media.count() == 1
        assert media.file.name.startswith("post_media/")

    @pytest.mark.django_db
    def test_media_instance_save_requires_a_post(self) -> None:
        orphan = PostMedia(media_type="image", order=0)
        orphan.file.save("orphan.png", ContentFile(b"data"), save=False)

        with pytest.raises(ValidationError, match=ERROR_MEDIA_POST_REQUIRED):
            orphan.save()


class TestPostMediaStorage:
    @pytest.mark.django_db
    def test_media_stored_under_the_post_media_path(self) -> None:
        post = _make_post(_make_user())

        media = _media(post, order=0, name="stored.png")
        media.save()

        stored = PostMedia.objects.get(pk=media.pk)

        assert stored.file.name.startswith("post_media/")
        assert Path(stored.file.path).is_relative_to(Path(settings.MEDIA_ROOT) / "post_media")
        assert stored.file.storage.exists(stored.file.name)
        assert stored.file.url == f"{settings.MEDIA_URL}{stored.file.name}"
