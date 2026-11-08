import uuid
from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostService

ERROR_POST_NOT_FOUND = "Post not found"


@dataclass(frozen=True, slots=True)
class GetPostInput:
    """Detail request submitted by an adapter (web view or API)."""

    user: User
    post_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class GetPostOutput:
    """Result of fetching a single post."""

    success: bool
    post: Post | None = None
    error: str | None = None


class GetPostUseCase:
    """Fetch a single post by identifier for the authenticated user.

    Visibility rule: only the owner's own post is returned. Another
    user's post is reported with the same explicit "Post not found"
    error as an unknown identifier (the post is treated as
    non-existent for non-owners, so existence is never leaked).
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def execute(self, input_dto: GetPostInput) -> GetPostOutput:
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None or post.owner_id != input_dto.user.pk:
            return GetPostOutput(success=False, error=ERROR_POST_NOT_FOUND)
        return GetPostOutput(success=True, post=post)
