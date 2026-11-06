"""Models for the posts domain (design decision 1): Post and PostMedia.

Ownership rules live on the model (design decision 2) so use cases can
translate ``can_edit``/``can_delete`` into success/error outputs without
duplicating the messages.
"""

import uuid
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from apps.accounts.models import User

CAPTION_MAX_LENGTH = 2200

# Field-level message for a caption over the limit; the DRF CharField default
# wording is kept so the API serializer (task group 3) reports the same text.
CAPTION_TOO_LONG_ERROR = "Ensure this caption has no more than 2200 characters."

# Spec ownership error texts (delta spec: Caption update / Post deletion).
POST_EDIT_NOT_OWNER_ERROR = "You can only edit your own posts"
POST_DELETE_NOT_OWNER_ERROR = "You can only delete your own posts"


class MediaType(models.TextChoices):
    """Kind of media attached to a post."""

    IMAGE = "image", "Image"
    VIDEO = "video", "Video"


class Post(models.Model):
    """A user post: optional caption (max 2200) plus up to 10 media files."""

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
        ordering = ["-created_at"]
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


class PostMedia(models.Model):
    """A media file attached to a post, with a zero-based order."""

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
