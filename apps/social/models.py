"""Models for the social domain (design decision 1): the Follow
relationship."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Follow(models.Model):
    """A directed follow relationship: ``follower`` follows ``following``."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("follower", "following")]
        constraints = [
            models.CheckConstraint(
                condition=~Q(follower=F("following")),
                name="no_self_follow",
            ),
        ]
        indexes = [
            models.Index(fields=["follower", "-created_at"]),
            models.Index(fields=["following", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Follow {self.follower_id} -> {self.following_id}"
