import threading
import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

CAPTION_MAX_LENGTH = 2200
MEDIA_LIMIT = 10
STORY_LIFETIME = timedelta(hours=24)

ERROR_CAPTION_TOO_LONG = "Caption cannot exceed 2200 characters"
ERROR_CAPTION_NOT_TEXT = "Caption must be plain text"
ERROR_MEDIA_LIMIT_EXCEEDED = "A post cannot have more than 10 media files"
ERROR_MEDIA_POST_REQUIRED = "Post media requires a post"
ERROR_STORY_EXPIRY_MISMATCH = "Story expiry must be exactly created_at plus 24 hours"


def validate_caption(value: object) -> None:
    """The model's caption validation error: `django.core.exceptions.ValidationError`."""
    if not isinstance(value, str):
        raise ValidationError(ERROR_CAPTION_NOT_TEXT)
    if len(value) > CAPTION_MAX_LENGTH:
        raise ValidationError(ERROR_CAPTION_TOO_LONG)


_bulk_write_state = threading.local()


def _internal_bulk_write_active() -> bool:
    return getattr(_bulk_write_state, "active", False)


@contextmanager
def _bulk_write():
    """Mark the enclosing queryset bulk write as internal machinery."""
    previous_state = getattr(_bulk_write_state, "active", False)
    _bulk_write_state.active = True
    try:
        yield
    finally:
        _bulk_write_state.active = previous_state


class PostQuerySet(models.QuerySet):
    """QuerySet that enforces the caption rule on every bulk write path."""

    def update(self, **kwargs) -> int:  # type: ignore[override]
        if "caption" in kwargs and not _internal_bulk_write_active():
            try:
                validate_caption(kwargs["caption"])
            except ValidationError:
                # Over-limit literals and non-literal expressions store
                # nothing and report zero updated rows without raising.
                return 0
        return super().update(**kwargs)

    def bulk_create(self, objs, *args, **kwargs):  # type: ignore[override]
        objs = tuple(objs)
        kept = []
        for obj in objs:
            if not isinstance(obj.caption, str):
                # Non-literal captions refuse the whole write.
                validate_caption(obj.caption)
            elif len(obj.caption) <= CAPTION_MAX_LENGTH:
                kept.append(obj)
        return super().bulk_create(kept, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):  # type: ignore[override]
        objs = tuple(objs)
        if "caption" in fields:
            kept = []
            for obj in objs:
                if not isinstance(obj.caption, str):
                    # Non-literal captions refuse the whole write.
                    validate_caption(obj.caption)
                elif len(obj.caption) <= CAPTION_MAX_LENGTH:
                    kept.append(obj)
            objs = kept
        with _bulk_write():
            return super().bulk_update(objs, fields, *args, **kwargs)


class PostManager(models.Manager.from_queryset(PostQuerySet)):  # type: ignore[misc]
    """Default manager with bulk-write caption enforcement."""


class Post(models.Model):
    """A user's post: optional caption plus up to 10 ordered media files."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name="owner",
    )
    caption = models.TextField("caption", blank=True, default="", validators=[validate_caption])
    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    objects: ClassVar[PostManager] = PostManager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "created_at"])]

    def __str__(self) -> str:
        return f"{self.owner} post {self.pk}"

    def save(self, *args, **kwargs):
        """Enforce the caption rule on the direct storage path.

        The bulk-write interception covers the queryset paths; this override
        refuses an over-limit or non-literal caption with the model's caption
        validation error before anything is stored.
        """
        validate_caption(self.caption)
        super().save(*args, **kwargs)

    def can_edit(self, user: AbstractBaseUser | None) -> bool:
        """Only the owner may update the post's caption."""
        return user is not None and self.owner_id == user.pk

    def can_delete(self, user: AbstractBaseUser | None) -> bool:
        """Only the owner may delete the post (its media goes with it)."""
        return user is not None and self.owner_id == user.pk


class PostMediaQuerySet(models.QuerySet):
    """QuerySet that enforces the media limit on every bulk write path."""

    def _existing_counts(self, post_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
        rows = (
            self.model._default_manager.filter(post_id__in=post_ids)
            .values("post_id")
            .annotate(total=models.Count("id"))
        )
        return {row["post_id"]: row["total"] for row in rows}

    def update(self, **kwargs) -> int:  # type: ignore[override]
        if not _internal_bulk_write_active() and ("post" in kwargs or "post_id" in kwargs):
            normalized = self._normalize_post_kwargs(kwargs)
            if normalized is None:
                # Django resolves both "post" and "post_id" to the same FK
                # column, so when the two names disagree the stored value is
                # order-dependent (last one wins) and cannot be simulated
                # against one target; a non-literal value cannot be counted
                # either. Consistent with the update() contract for
                # non-literal input, nothing is stored and zero rows are
                # reported without raising.
                return 0
            return self._update_respecting_capacity(normalized)
        return super().update(**kwargs)

    def _normalize_post_kwargs(self, kwargs: dict) -> dict | None:
        """Resolve the post kwargs to ONE canonical target, or refuse.

        "post" and "post_id" name the same FK column: a call carrying both
        stores only the last value while the simulation must protect exactly
        what would be stored. If the names disagree (or a value is a
        non-literal expression) there is no simulable single target and the
        caller refuses the write; otherwise only one canonical name survives
        so the simulated and stored targets cannot diverge.
        """
        present = [key for key in ("post", "post_id") if key in kwargs]
        if len(present) == 1:
            return kwargs
        first, second = (self._literal_post_id(kwargs[key]) for key in present)
        if first is None or first != second:
            return None
        normalized = {key: value for key, value in kwargs.items() if key not in present}
        normalized[present[-1]] = kwargs[present[-1]]
        return normalized

    @staticmethod
    def _literal_post_id(target) -> uuid.UUID | None:
        """The literal post id a kwarg value resolves to, or None."""
        if hasattr(target, "resolve_expression"):
            return None
        return getattr(target, "pk", target)

    def _update_respecting_capacity(self, kwargs: dict) -> int:
        for key in ("post", "post_id"):
            if key in kwargs:
                target = kwargs[key]
                break
        if hasattr(target, "resolve_expression"):
            # Non-literal post values cannot be counted: store nothing,
            # report zero updated rows without raising.
            return 0
        post_id = getattr(target, "pk", target)
        # Rows of this queryset already in the target post keep their
        # update: they do not consume a new slot. Only rows moving in
        # compete for the remaining capacity.
        keeping = list(self.filter(post_id=post_id).values_list("pk", flat=True))
        remaining = MEDIA_LIMIT - self._existing_counts({post_id}).get(post_id, 0)
        moving = (
            list(self.exclude(post_id=post_id).values_list("pk", flat=True)[:remaining])
            if remaining > 0
            else []
        )
        fitting = keeping + moving
        if not fitting:
            return 0
        with _bulk_write():
            return self.filter(pk__in=fitting).update(**kwargs)

    def bulk_create(self, objs, *args, **kwargs):  # type: ignore[override]
        objs = tuple(objs)
        for obj in objs:
            if obj.post_id is None:
                raise ValidationError(ERROR_MEDIA_POST_REQUIRED)
        counts = self._existing_counts({obj.post_id for obj in objs})
        kept = []
        for obj in objs:
            if counts.get(obj.post_id, 0) < MEDIA_LIMIT:
                kept.append(obj)
                counts[obj.post_id] = counts.get(obj.post_id, 0) + 1
        return super().bulk_create(kept, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):  # type: ignore[override]
        objs = tuple(objs)
        if "post" in fields or "post_id" in fields:
            # Django accepts both the field name and its attname
            # ("post_id"): both carry the same move and must go through
            # the same capacity simulation.
            objs = self._keep_rows_that_fit(objs)
        with _bulk_write():
            return super().bulk_update(objs, fields, *args, **kwargs)

    def _keep_rows_that_fit(self, objs: tuple) -> list:
        """Keep only the rows whose post move fits the media limit.

        The post change is simulated row by row in write order: a row moving
        into a post consumes one slot, a row moving out of its post frees
        one. Rows whose post does not change are always kept (they do not
        affect the capacity of any post).
        """
        for obj in objs:
            if obj.post_id is None:
                raise ValidationError(ERROR_MEDIA_POST_REQUIRED)
        current = dict(self.filter(pk__in=[obj.pk for obj in objs]).values_list("pk", "post_id"))
        origins = {post_id for post_id in current.values() if post_id is not None}
        counts = self._existing_counts({obj.post_id for obj in objs} | origins)
        kept = []
        for obj in objs:
            origin = current.get(obj.pk)
            if origin == obj.post_id:
                kept.append(obj)
                continue
            if counts.get(obj.post_id, 0) < MEDIA_LIMIT:
                kept.append(obj)
                counts[obj.post_id] = counts.get(obj.post_id, 0) + 1
                if origin is not None:
                    counts[origin] = max(counts.get(origin, 0) - 1, 0)
        return kept


class PostMediaManager(models.Manager.from_queryset(PostMediaQuerySet)):  # type: ignore[misc]
    """Default manager with bulk-write media-limit enforcement."""


class PostMedia(models.Model):
    """A media file attached to a post, ordered within the post."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name="post",
    )
    file = models.FileField("media file", upload_to="post_media/")
    media_type = models.CharField("media type", max_length=5, choices=MediaType.choices)
    order = models.PositiveIntegerField("order", default=0)

    objects: ClassVar[PostMediaManager] = PostMediaManager()

    class Meta:
        ordering = ["post", "order"]
        indexes = [models.Index(fields=["post", "order"])]

    def __str__(self) -> str:
        return f"{self.post} media {self.order}"

    def save(self, *args, **kwargs):
        """Enforce the media limit on the direct storage path.

        The bulk-write interception covers the queryset paths; this override
        refuses a new media file that would exceed the post's capacity and a
        move of an existing row into a full post with the model's media
        validation error.
        """
        if self.post_id is None:
            raise ValidationError(ERROR_MEDIA_POST_REQUIRED)
        if self._state.adding:
            total = PostMedia._default_manager.filter(post_id=self.post_id).count()
            if total >= MEDIA_LIMIT:
                raise ValidationError(ERROR_MEDIA_LIMIT_EXCEEDED)
        elif self._post_changed():
            total = (
                PostMedia._default_manager.filter(post_id=self.post_id).exclude(pk=self.pk).count()
            )
            if total >= MEDIA_LIMIT:
                raise ValidationError(ERROR_MEDIA_LIMIT_EXCEEDED)
        super().save(*args, **kwargs)

    def _post_changed(self) -> bool:
        """Whether this row is being moved to a different post than its DB one."""
        if self.pk is None:
            return True
        stored_post_id = (
            PostMedia._default_manager.filter(pk=self.pk).values_list("post_id", flat=True).first()
        )
        return stored_post_id != self.post_id


class StoryQuerySet(models.QuerySet):
    """QuerySet with the active-stories filter shared by every stories feature."""

    def active(self) -> "StoryQuerySet":
        """Stories whose expiration timestamp has not passed yet."""
        return self.filter(expires_at__gt=timezone.now())


class StoryManager(models.Manager.from_queryset(StoryQuerySet)):  # type: ignore[misc]
    """Default manager with the active-stories filter."""


class Story(models.Model):
    """A user's ephemeral image story that expires 24 hours after creation."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
        verbose_name="owner",
    )
    image = models.ImageField("image", upload_to="stories/%Y/%m/%d/")
    media_type = models.CharField(
        "media type", max_length=5, choices=MediaType.choices, default=MediaType.IMAGE
    )
    created_at = models.DateTimeField("created at", default=timezone.now, editable=False)
    expires_at = models.DateTimeField("expires at")

    objects: ClassVar[StoryManager] = StoryManager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "expires_at"])]

    def __str__(self) -> str:
        return f"{self.owner} story {self.pk}"

    def save(self, *args, **kwargs):
        """Enforce the 24-hour lifetime invariant on the storage path.

        A story saved without an expiration timestamp gets exactly
        `created_at + 24h`; an explicitly provided expiration that differs
        is refused with the model's expiry validation error before anything
        is stored.
        """
        expected = self.created_at + STORY_LIFETIME
        if self.expires_at is None:
            self.expires_at = expected
        elif self.expires_at != expected:
            raise ValidationError(ERROR_STORY_EXPIRY_MISMATCH)
        super().save(*args, **kwargs)


class StoryView(models.Model):
    """A single view of a story by a user, recorded at most once per pair."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="views",
        verbose_name="story",
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="story_views",
        verbose_name="viewer",
    )
    viewed_at = models.DateTimeField("viewed at", auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["story", "viewer"],
                name="unique_story_view_story_viewer",
            )
        ]
        indexes = [models.Index(fields=["viewer"])]

    def __str__(self) -> str:
        return f"{self.story} viewed by {self.viewer}"
