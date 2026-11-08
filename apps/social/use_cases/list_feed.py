from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.services import FeedService


@dataclass(frozen=True, slots=True)
class ListFeedInput:
    """Feed request submitted by an adapter (web view)."""

    user: User
    limit: int | None = None
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListFeedOutput:
    """One window of the followed-users feed plus the empty-state signal."""

    success: bool
    posts: list[Post]
    follows_anyone: bool
    error: str | None = None


class ListFeedUseCase:
    """List the posts of the users the requester follows, newest first.

    Visibility rule: the feed only ever touches posts of followed users;
    the requester's own posts and strangers' posts are unreachable
    through it. The `follows_anyone` signal carries the empty-state
    distinction (no follows vs. follows without posts) to the adapter.
    """

    def __init__(self, feed_service: FeedService) -> None:
        self._feed_service = feed_service

    def execute(self, input_dto: ListFeedInput) -> ListFeedOutput:
        page = self._feed_service.list_feed(
            input_dto.user, limit=input_dto.limit, offset=input_dto.offset
        )
        return ListFeedOutput(
            success=True,
            posts=page.posts,
            follows_anyone=page.follows_anyone,
        )
