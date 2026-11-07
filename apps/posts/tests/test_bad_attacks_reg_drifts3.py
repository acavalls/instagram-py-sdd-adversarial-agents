"""The Bad — attack iteration 3 on change ``regularize-social-drifts``.

Targets the queryset guards The Good added for BUG-R003/BUG-R004 with fresh
angles: caption bypasses on the Post bulk paths the fix did not cover
(``bulk_update``/``bulk_create``), partial-application accounting on mixed
bulk_update reassignments, no-op self-reassignment, capacity accounting
after deletions, and atomicity of the username bulk_update guard on mixed
batches.
"""

from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.posts.models import CAPTION_MAX_LENGTH, MEDIA_MAX_COUNT, Post, PostMedia

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


def fill_post(post: Post, count: int, order_base: int = 0) -> None:
    PostMedia.objects.bulk_create(
        [
            PostMedia(
                post=post,
                image=make_media_file(f"{post.pk}-{order_base + i}.gif"),
                order=order_base + i,
            )
            for i in range(count)
        ]
    )


class TestCaptionBulkPathBypass:
    def test_atk_r024_post_bulk_update_caption_over_limit(self):
        """BUG-R004 follow-up: the fix guards ``PostQuerySet.update()`` with a
        literal-caption check, but Django's ``QuerySet.bulk_update()`` is a
        separate batched-write path that never calls ``Model.save()`` and has
        NO override on ``PostQuerySet``. The living spec (posts, Post data
        model): 'WHEN a post is created or updated with a caption longer than
        2200 characters, THE SYSTEM SHALL reject the write' — bulk_update is
        an update."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="harmless")
        post.caption = "x" * (CAPTION_MAX_LENGTH + 1)
        Post.objects.bulk_update([post], ["caption"])
        persisted = Post.objects.get(pk=post.pk)
        assert len(persisted.caption) <= CAPTION_MAX_LENGTH, (
            f"bulk_update persisted an over-limit caption of length {len(persisted.caption)}"
        )

    def test_atk_r025_post_bulk_create_caption_over_limit(self):
        """Same bypass family on the creation path: the spec scenario covers
        'created ... with a caption longer than 2200'; ``Post.objects`` is a
        ``from_queryset`` manager with no ``bulk_create`` override, so the
        batched INSERT never runs ``Post.save()``."""
        user = make_user()
        hostile = Post(owner=user, caption="y" * (CAPTION_MAX_LENGTH + 1))
        Post.objects.bulk_create([hostile])
        assert not Post.objects.filter(
            owner=user, caption="y" * (CAPTION_MAX_LENGTH + 1)
        ).exists(), "bulk_create persisted an over-limit caption"


class TestMediaGuardFreshAngles:
    def test_atk_r026_bulk_update_mixed_targets_no_violation_written(self):
        """BUG-R003 fix, new angle: one bulk_update reassigning rows onto TWO
        targets — one full, one with room. The invariant that matters to the
        delta is that the FULL post never gains a row; nothing from the
        violating target may be written regardless of what happens to the
        other target's rows (per-target accounting, not per-call refusal)."""
        user = make_user()
        full = Post.objects.create(owner=user, caption="full")
        roomy = Post.objects.create(owner=user, caption="roomy")
        fill_post(full, MEDIA_MAX_COUNT)
        donors = [Post.objects.create(owner=user, caption=f"d{i}") for i in range(4)]
        moving = []
        for i, donor in enumerate(donors):
            media = PostMedia.objects.create(
                post=donor, image=make_media_file(f"m{i}.gif"), order=i
            )
            moving.append(media)
        # Two rows onto the FULL post (violating), two onto the roomy post.
        moving[0].post = full
        moving[1].post = full
        moving[2].post = roomy
        moving[3].post = roomy
        PostMedia.objects.bulk_update(moving, ["post"])
        assert PostMedia.objects.filter(post=full).count() == MEDIA_MAX_COUNT, (
            "full post gained rows"
        )
        donors_total = sum(PostMedia.objects.filter(post=d).count() for d in donors)
        assert PostMedia.objects.filter(post=roomy).count() + donors_total == 4, (
            "rows vanished or were duplicated by the mixed reassignment"
        )

    def test_atk_r027_update_to_own_post_is_noop(self):
        """BUG-R003 fix, new angle: ``update(post=<row's own post>)`` is a
        no-op on a full post — the guard must not refuse it (rows already on
        the target are excluded from the capacity count) and must not write
        anything surprising."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="self")
        fill_post(post, MEDIA_MAX_COUNT)
        affected = PostMedia.objects.filter(post=post).update(post=post)
        assert affected == MEDIA_MAX_COUNT
        assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT

    def test_atk_r028_post_update_valid_caption_still_works(self):
        """BUG-R004 fix regression angle: a legal literal caption update via
        the guarded queryset must still be written."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="old")
        updated = Post.objects.filter(pk=post.pk).update(caption="new valid caption")
        post.refresh_from_db()
        assert updated == 1
        assert post.caption == "new valid caption"

    def test_atk_r029_media_capacity_after_deletions(self):
        """Capacity accounting must read the LIVE count: fill to 10, delete
        one, then bulk_create two — exactly one may land (room=1), the other
        must be dropped, keeping the post at 10."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="del")
        fill_post(post, MEDIA_MAX_COUNT)
        PostMedia.objects.filter(post=post, order=0).delete()
        assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT - 1
        PostMedia.objects.bulk_create(
            [
                PostMedia(post=post, image=make_media_file(f"new{i}.gif"), order=50 + i)
                for i in range(2)
            ]
        )
        assert PostMedia.objects.filter(post=post).count() == MEDIA_MAX_COUNT, (
            "post exceeded 10 after delete+create"
        )


class TestUsernameBulkAtomicity:
    def test_atk_r030_user_bulk_update_mixed_batch_atomic_refusal(self):
        """R018 fix, new angle: a mixed batch (one valid user, one hostile)
        must be refused ATOMICALLY — the valid user's write must not land
        either, since the guard validates before calling super()."""
        good = make_user(username="gooduser", email="good@x.com")
        bad = make_user(username="baduser", email="bad@x.com")
        good.username = "renamed-good"
        bad.username = "UPPER!"  # violates the lowercase-underscore rule
        with pytest.raises(ValidationError):
            User.objects.bulk_update([good, bad], ["username"])
        good.refresh_from_db()
        bad.refresh_from_db()
        assert good.username == "gooduser", "valid row was written despite atomic refusal"
        assert bad.username == "baduser", "hostile row was written"
