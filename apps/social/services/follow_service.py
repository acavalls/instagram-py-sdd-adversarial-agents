from dataclasses import dataclass

from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.social.models import Follow

ERROR_SELF_FOLLOW = "You cannot follow yourself"
ERROR_ALREADY_FOLLOWING = "Already following this user"
ERROR_FOLLOW_NOT_FOUND = "Follow relationship not found"


@dataclass(frozen=True, slots=True)
class FollowOutput:
    """Result of creating a follow relationship."""

    success: bool
    follow: Follow | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class UnfollowOutput:
    """Result of removing a follow relationship."""

    success: bool
    error: str | None = None


class FollowService:
    """Domain service for follow relationship persistence and queries."""

    def follow(self, *, follower: User, following: User) -> FollowOutput:
        """Create the (follower, following) relationship.

        Self-follow is refused explicitly before any insert; a duplicate
        pair is refused by the database's unique constraint and mapped to
        the friendly error (the last line of defense, also covering
        concurrent inserts).
        """
        if follower == following:
            return FollowOutput(success=False, error=ERROR_SELF_FOLLOW)
        try:
            with transaction.atomic():
                follow = Follow.objects.create(follower=follower, following=following)
        except IntegrityError:
            return FollowOutput(success=False, error=ERROR_ALREADY_FOLLOWING)
        return FollowOutput(success=True, follow=follow)

    def unfollow(self, *, follower: User, following: User) -> UnfollowOutput:
        """Remove the (follower, following) relationship if it exists."""
        deleted, _ = Follow.objects.filter(follower=follower, following=following).delete()
        if not deleted:
            return UnfollowOutput(success=False, error=ERROR_FOLLOW_NOT_FOUND)
        return UnfollowOutput(success=True)

    def is_following(self, follower: User, following: User) -> bool:
        """Whether `follower` currently follows `following`."""
        return Follow.objects.filter(follower=follower, following=following).exists()

    def get_following(self, user: User) -> list[User]:
        """The users `user` follows, newest relationship first."""
        queryset = Follow.objects.filter(follower=user).select_related("following")
        return [follow.following for follow in queryset]

    def get_followers(self, user: User) -> list[User]:
        """The users following `user`, newest relationship first."""
        queryset = Follow.objects.filter(following=user).select_related("follower")
        return [follow.follower for follow in queryset]
