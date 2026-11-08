import uuid

from django.conf import settings
from django.db import models


class Follow(models.Model):
    """A directed follow relationship: `follower` follows `following`.

    The database enforces the invariants directly: a (follower, following)
    pair is unique and a user cannot follow themselves (check constraint).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_set",
        verbose_name="follower",
        help_text="The user who follows.",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers_set",
        verbose_name="following",
        help_text="The user being followed.",
    )
    created_at = models.DateTimeField("created at", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="social_follow_unique_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="social_follow_no_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.follower} follows {self.following}"
