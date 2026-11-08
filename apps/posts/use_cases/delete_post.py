import uuid
from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.services import PostService
from apps.posts.use_cases.get_post import ERROR_POST_NOT_FOUND

ERROR_POST_DELETE_FORBIDDEN = "You can only delete your own posts"


@dataclass(frozen=True, slots=True)
class DeletePostInput:
    """Deletion request submitted by an adapter (web view or API)."""

    user: User
    post_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class DeletePostOutput:
    """Result of deleting a post."""

    success: bool
    error: str | None = None


class DeletePostUseCase:
    """Delete a post owned by the submitting user, media included.

    Ownership lives in the model (`Post.can_delete`); a non-owner is
    refused with the explicit ownership error the adapters map to 403.
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def execute(self, input_dto: DeletePostInput) -> DeletePostOutput:
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None:
            return DeletePostOutput(success=False, error=ERROR_POST_NOT_FOUND)
        if not post.can_delete(input_dto.user):
            return DeletePostOutput(success=False, error=ERROR_POST_DELETE_FORBIDDEN)
        result = self._post_service.delete(post=post)
        return DeletePostOutput(success=result.success, error=result.error)
