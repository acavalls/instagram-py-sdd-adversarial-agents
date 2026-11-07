"""Models for the posts domain (design decision 1): Post and PostMedia.

Ownership rules live on the model (design decision 2) so use cases can
translate ``can_edit``/``can_delete`` into success/error outputs without
duplicating the messages.
"""

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import User

CAPTION_MAX_LENGTH = 2200

# Field-level message for a caption over the limit; the DRF CharField default
# wording is kept so the API serializer (task group 3) reports the same text.
CAPTION_TOO_LONG_ERROR = "Ensure this caption has no more than 2200 characters."

# Model-level media limit (spec: Post creation — "up to 10 media files");
# ``PostMedia.save`` enforces it on EVERY persistence path (design decision 3),
# mirroring the caption save-guard. The API serializer reuses the same message
# so both paths report the same text.
MEDIA_MAX_COUNT = 10
MEDIA_TOO_MANY_ERROR = "A post can have at most 10 media files."

# Spec ownership error texts (delta spec: Caption update / Post deletion).
POST_EDIT_NOT_OWNER_ERROR = "You can only edit your own posts"
POST_DELETE_NOT_OWNER_ERROR = "You can only delete your own posts"

# Spec story lifetime (delta spec: Story data model — "an expiration
# timestamp set to 24 hours after creation"). ``Story.save`` enforces it on
# EVERY persistence path, mirroring the caption/media save-guards.
STORY_EXPIRY_HOURS = 24


class MediaType(models.TextChoices):
    """Kind of media attached to a post."""

    IMAGE = "image", "Image"
    VIDEO = "video", "Video"


class PostQuerySet(models.QuerySet["Post"]):
    """QuerySet that keeps the caption limit un-bypassable on bulk writes.

    ``QuerySet.update()`` and ``bulk_create()`` never call ``Model.save()``
    (Django semantics), so without these overrides an over-limit caption
    would be stored through them despite the ``Post.save`` guard (BUG-R004,
    BUG-R005). Mirroring the ``UserQuerySet.update`` pattern
    (apps/accounts/models.py), a literal string caption is validated against
    ``CAPTION_MAX_LENGTH`` and a non-literal value (e.g. ``F()``/
    ``Combinable`` expressions) has no text to validate. In both violating
    cases the write is refused and the whole ``update()`` call writes
    nothing. The repro tests pin silent refusal (no exception), so — unlike
    the username guard, which raises — the refusal here returns ``0``
    without writing (BUG-R004 fix, 2026-11-07; the delta scenario "Caption
    length limit" is satisfied by the caption never being stored).
    ``bulk_create()`` follows the same silent-refusal contract: over-limit
    literal captions are dropped from the batch (mirroring the
    ``PostMediaQuerySet.bulk_create`` store-only-what-fits semantics) while
    a non-literal caption is refused with the model's caption
    ``ValidationError`` (BUG-R005 adjudicated semantics: rejection with a
    validation error).
    """

    def update(self, **kwargs: Any) -> int:
        if "caption" in kwargs:
            caption = kwargs["caption"]
            if not isinstance(caption, str) or len(caption) > CAPTION_MAX_LENGTH:
                # Over-limit literal or non-literal expression: the caption
                # rule cannot be honored, so nothing is written at all.
                return 0
        return super().update(**kwargs)

    def bulk_create(self, objs: Any, *args: Any, **kwargs: Any) -> Any:
        """Refuse to persist over-limit captions through the batched INSERT.

        Typed loosely (``Any``) on purpose: the project's django-stubs version
        leaves ``QuerySet`` subclasses generic, so a strictly typed override
        cannot stay compatible with ``QuerySet.bulk_create``. ``objs`` may be
        any iterable, so it is materialized before validation. Each literal
        caption is validated against ``CAPTION_MAX_LENGTH``: an over-limit
        caption is dropped from the batch (nothing is persisted, matching the
        pinned silent-refusal contract of the caption guards in this module),
        and a non-literal caption (no text to validate) is refused with the
        model's caption ``ValidationError`` (BUG-R005 adjudication).
        """
        allowed: list[Any] = []
        for obj in objs:
            if not isinstance(obj.caption, str):
                raise ValidationError({"caption": [CAPTION_TOO_LONG_ERROR]})
            if len(obj.caption) > CAPTION_MAX_LENGTH:
                continue
            allowed.append(obj)
        return super().bulk_create(allowed, *args, **kwargs)


class PostManager(models.Manager.from_queryset(PostQuerySet)):  # type: ignore[misc]
    """Manager exposing the bulk-write caption guard as the default manager.

    Same ``from_queryset`` idiom as ``UserManager`` (accounts), so
    ``Post.objects.update(...)`` enforces the caption limit. The
    ``type: ignore`` covers mypy's "unsupported dynamic base class" for the
    ``from_queryset`` idiom.
    """


class Post(models.Model):
    """A user post: optional caption (max 2200) plus up to 10 media files."""

    # The rule-enforcing manager (bulk writes cannot bypass the caption limit).
    objects: ClassVar[PostManager] = PostManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    caption = models.CharField(
        max_length=CAPTION_MAX_LENGTH,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest first, with the identifier as tiebreaker (design decision 2):
        # posts created within the same clock tick keep a deterministic order,
        # so pagination windows are stable and duplicate-free.
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Post {self.pk} by {self.owner_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Enforce the caption limit on EVERY persistence path.

        ``CharField.max_length`` is only checked by ``full_clean()``/forms;
        a bare ``save()`` (shell, services) would persist an over-long
        caption otherwise. Mirrors ``User.save`` enforcing the username rule.
        """
        if len(self.caption) > CAPTION_MAX_LENGTH:
            raise ValidationError({"caption": [CAPTION_TOO_LONG_ERROR]})
        super().save(*args, **kwargs)

    @classmethod
    def can_edit(cls, post: "Post", user: "User | None") -> tuple[bool, str | None]:
        """Ownership rule for caption updates (design decision 2).

        Returns ``(True, None)`` when ``user`` owns ``post``; otherwise
        ``(False, POST_EDIT_NOT_OWNER_ERROR)`` with the spec message.
        """
        if user is None or post.owner_id != user.pk:
            return False, POST_EDIT_NOT_OWNER_ERROR
        return True, None

    @classmethod
    def can_delete(cls, post: "Post", user: "User | None") -> tuple[bool, str | None]:
        """Ownership rule for deletions (design decision 2).

        Returns ``(True, None)`` when ``user`` owns ``post``; otherwise
        ``(False, POST_DELETE_NOT_OWNER_ERROR)`` with the spec message.
        """
        if user is None or post.owner_id != user.pk:
            return False, POST_DELETE_NOT_OWNER_ERROR
        return True, None


class PostMediaQuerySet(models.QuerySet["PostMedia"]):
    """QuerySet that keeps the media-count invariant un-bypassable on bulk writes.

    ``QuerySet.bulk_create()``, ``bulk_update()`` and ``update()`` never call
    ``Model.save()`` (Django semantics), so without these overrides media
    could be attached to a post beyond ``MEDIA_MAX_COUNT`` despite the
    ``PostMedia.save`` guard (BUG-R001, BUG-R003). Mirroring the
    ``UserQuerySet`` override pattern (apps/accounts/models.py), each
    override runs a pre-write per-post capacity check. ``bulk_create()``
    stores only the rows that fit within the limit; ``bulk_update()``/
    ``update()`` reassignments onto a post without room are never written
    (BUG-R003 fix, 2026-11-07). The repro tests pin silent refusal (no
    exception), so the refusals drop the offending rows / write nothing
    instead of raising, and the spec's "up to 10 ordered files attached to
    a post" holds on every persistence path.
    """

    def bulk_create(self, objs: Any, *args: Any, **kwargs: Any) -> Any:
        """Store only the per-post rows that fit within the media limit.

        Typed loosely (``Any``) on purpose: the project's django-stubs version
        leaves ``QuerySet`` subclasses generic, so a strictly typed override
        cannot stay compatible with ``QuerySet.bulk_create``. ``objs`` may be
        any iterable (e.g. the generator ``PostService.create`` passes), so it
        is materialized here before the per-post capacity accounting.
        """
        allowed: list[Any] = []
        remaining: dict[uuid.UUID | None, int] = {}
        for obj in objs:
            post_id = obj.post_id
            if post_id not in remaining:
                existing = 0
                if post_id is not None:
                    existing = PostMedia.objects.filter(post_id=post_id).count()
                remaining[post_id] = MEDIA_MAX_COUNT - existing
            if remaining[post_id] > 0:
                remaining[post_id] -= 1
                allowed.append(obj)
        return super().bulk_create(allowed, *args, **kwargs)

    def update(self, **kwargs: Any) -> int:
        """Refuse reassignments that would exceed a target post's capacity.

        When the write touches ``post``/``post_id`` with a literal target,
        the rows in this queryset that are not already on the target post
        would each become a new file there; if the target has no room for
        all of them the whole ``update()`` writes nothing and returns ``0``
        (a single ``UPDATE`` cannot apply partially). A non-literal target
        (e.g. ``F()``) has no post to size, so it is refused the same way
        rather than persisting an unverifiable reassignment.
        """
        if "post" in kwargs or "post_id" in kwargs:
            target = kwargs.get("post", kwargs.get("post_id"))
            if isinstance(target, Post):
                target_id: uuid.UUID | str = target.pk
            elif isinstance(target, (str, uuid.UUID)):
                target_id = target
            else:
                return 0
            room = MEDIA_MAX_COUNT - PostMedia.objects.filter(post_id=target_id).count()
            if self.exclude(post_id=target_id).count() > room:
                return 0
        return super().update(**kwargs)

    def bulk_update(self, objs: Any, fields: Any, *args: Any, **kwargs: Any) -> Any:
        """Write only the reassigned rows that fit within the media limit.

        Same loose typing as ``bulk_create``. Each object's current post is
        read from the database (the in-memory ``post`` may already point at
        the new target), then per-target capacity accounting mirrors
        ``bulk_create``: rows already on their target are kept (no-op) and
        rows moving onto a post without room are never written.
        """
        if {"post", "post_id"} & set(fields):
            batch = list(objs)
            db_posts = dict(
                PostMedia.objects.filter(
                    pk__in=[o.pk for o in batch if o.pk is not None]
                ).values_list("pk", "post_id")
            )
            remaining: dict[uuid.UUID | None, int] = {}
            allowed: list[Any] = []
            for obj in batch:
                target_id = obj.post_id
                if target_id is None:
                    # Required FK: keep the row so ``super()`` surfaces
                    # Django's own error for the NULL write, as before.
                    allowed.append(obj)
                    continue
                if target_id not in remaining:
                    existing = PostMedia.objects.filter(post_id=target_id).count()
                    remaining[target_id] = MEDIA_MAX_COUNT - existing
                if db_posts.get(obj.pk) == target_id:
                    allowed.append(obj)
                elif remaining[target_id] > 0:
                    remaining[target_id] -= 1
                    allowed.append(obj)
            return super().bulk_update(allowed, fields, *args, **kwargs)
        return super().bulk_update(objs, fields, *args, **kwargs)


class PostMediaManager(models.Manager.from_queryset(PostMediaQuerySet)):  # type: ignore[misc]
    """Manager exposing the bulk-write media-count guard as the default manager.

    Same ``from_queryset`` idiom as ``UserManager`` (accounts), so
    ``PostMedia.objects.bulk_create(...)`` — and the related manager
    ``post.media.bulk_create(...)`` derived from it — enforce the limit.
    The ``type: ignore`` covers mypy's "unsupported dynamic base class" for
    the ``from_queryset`` idiom.
    """


class PostMedia(models.Model):
    """A media file attached to a post, with a zero-based order."""

    # The rule-enforcing manager (bulk writes cannot bypass the media limit).
    objects: ClassVar[PostMediaManager] = PostMediaManager()

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="media",
    )
    image = models.ImageField(upload_to="post_media/")
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]
        # (post, order) uniqueness keeps the zero-based ordering consistent
        # (max 10 media per post, one file per position). It also provides
        # the (post, order) index required by design decision 1.
        constraints = [
            models.UniqueConstraint(fields=["post", "order"], name="unique_post_order"),
        ]

    def __str__(self) -> str:
        return f"Media {self.pk} for post {self.post_id} (order {self.order})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Enforce the media limit on EVERY persistence path.

        A post holds at most 10 media files (spec: Post creation) and the
        database schema does not enforce the count; a bare ``save()`` (shell,
        services) would persist an 11th file otherwise. Mirrors
        ``Post.save`` enforcing the caption limit (design decision 3).
        """
        if (
            self.post_id
            and PostMedia.objects.filter(post_id=self.post_id).exclude(pk=self.pk).count()
            >= MEDIA_MAX_COUNT
        ):
            raise ValidationError({"post": [MEDIA_TOO_MANY_ERROR]})
        super().save(*args, **kwargs)


class Story(models.Model):
    """An ephemeral 24-hour story owned by a user (design decision 1).

    The media is always a generated placeholder image (deterministic-media
    principle); ``media_type`` keeps the image/video choice for parity but
    the creation flow only ever produces images.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
    )
    image = models.ImageField(upload_to="stories/%Y/%m/%d/")
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    # A callable default (instead of ``auto_now_add``) so the value is known
    # on the instance BEFORE the insert and ``save()`` can derive
    # ``expires_at`` from it: the expiration is exactly ``created_at`` + 24h
    # (spec scenario "Story persisted with placeholder media"), not
    # ``now() + 24h`` evaluated microseconds earlier.
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()

    class Meta:
        # Newest first, with the identifier as tiebreaker (same convention
        # as ``Post``): stories created within the same clock tick keep a
        # deterministic order.
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            # The lazy purge (design decision 6) filters on ``expires_at``.
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Story {self.pk} by {self.owner_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Set the 24h expiration on EVERY persistence path.

        A story lives exactly 24 hours (spec: Story data model) and nothing
        else enforces the lifetime; a bare ``save()`` (shell, services)
        without an explicit ``expires_at`` would either fail on the NOT NULL
        column or let a caller persist an arbitrary lifetime. Mirrors the
        ``Post.save`` guard pattern (design decision 1).
        """
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=STORY_EXPIRY_HOURS)
        super().save(*args, **kwargs)


class StoryView(models.Model):
    """A single (story, viewer) view record (design decision 1).

    The unique constraint makes a repeated ``mark_viewed`` idempotent at the
    database level (spec: Story view tracking — "at most once").
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="views",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="story_views",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["story", "viewer"], name="unique_story_viewer"),
        ]
        indexes = [
            # "Which stories has this viewer seen" lookups (feed stories are
            # decorated per viewer, design decision 2). The (story, viewer)
            # pair is already indexed by the unique constraint.
            models.Index(fields=["viewer", "story"]),
        ]

    def __str__(self) -> str:
        return f"StoryView {self.pk}: story {self.story_id} by {self.viewer_id}"
