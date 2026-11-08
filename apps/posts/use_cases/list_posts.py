from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostService


@dataclass(frozen=True, slots=True)
class ListPostsInput:
    """Listing request submitted by an adapter (web view or API)."""

    user: User
    limit: int | None = None
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListPostsOutput:
    """The requesting user's own posts, newest first."""

    success: bool
    posts: list[Post]
    error: str | None = None


class ListPostsUseCase:
    """List the authenticated user's own posts (no cross-user listing).

    Visibility rule: the listing only ever touches the owner's own
    posts; other users' posts are unreachable through it.
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def execute(self, input_dto: ListPostsInput) -> ListPostsOutput:
        posts = self._post_service.list_for_user(
            input_dto.user, limit=input_dto.limit, offset=input_dto.offset
        )
        return ListPostsOutput(success=True, posts=posts)
