from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow

SUGGESTIONS_LIMIT = 5


@dataclass(frozen=True, slots=True)
class FeedPage:
    """One window of the followed-users feed plus its empty-state signal.

    `follows_anyone` lets adapters distinguish the two empty cases the
    feed spec declares: no follows at all (primary empty state) versus
    follows without any followed posts (secondary empty state).
    """

    posts: list[Post]
    follows_anyone: bool


class FeedService:
    """Domain service for the followed-users feed and account suggestions."""

    def list_feed(
        self,
        user: User,
        limit: int | None = None,
        offset: int = 0,
    ) -> FeedPage:
        """List the posts of the users `user` follows, newest first.

        The posts are selected through a follow subquery (never a plain
        join-and-materialize) and the model's `Meta.ordering` (creation
        date descending, then identifier descending) provides the
        deterministic newest-first order; limit/offset carve the
        pagination window out of it.
        """
        followed_ids = Follow.objects.filter(follower=user).values("following")
        queryset = Post.objects.filter(owner__in=followed_ids).select_related("owner")
        if offset:
            queryset = queryset[offset:]
        if limit is not None:
            queryset = queryset[:limit]
        return FeedPage(posts=list(queryset), follows_anyone=followed_ids.exists())

    def get_suggestions(self, user: User, limit: int = SUGGESTIONS_LIMIT) -> list[User]:
        """Up to `limit` users `user` does not follow, newest accounts first.

        Self and every followed user are excluded; the ordering is the
        join date descending with the identifier descending as the
        deterministic tie-break.
        """
        followed_ids = Follow.objects.filter(follower=user).values("following")
        queryset = (
            User.objects.exclude(pk=user.pk)
            .exclude(pk__in=followed_ids)
            .order_by("-date_joined", "-pk")[:limit]
        )
        return list(queryset)
