import uuid
from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostService
from apps.posts.use_cases.get_post import ERROR_POST_NOT_FOUND

ERROR_POST_EDIT_FORBIDDEN = "You can only edit your own posts"


@dataclass(frozen=True, slots=True)
class UpdatePostInput:
    """Caption update submitted by an adapter (web view or API)."""

    user: User
    post_id: uuid.UUID
    caption: str


@dataclass(frozen=True, slots=True)
class UpdatePostOutput:
    """Result of updating a post's caption."""

    success: bool
    post: Post | None = None
    error: str | None = None


class UpdatePostUseCase:
    """Update the caption of a post owned by the submitting user.

    Ownership lives in the model (`Post.can_edit`); a non-owner is
    refused with the explicit ownership error the adapters map to 403.
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def execute(self, input_dto: UpdatePostInput) -> UpdatePostOutput:
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None:
            return UpdatePostOutput(success=False, error=ERROR_POST_NOT_FOUND)
        if not post.can_edit(input_dto.user):
            return UpdatePostOutput(success=False, error=ERROR_POST_EDIT_FORBIDDEN)
        result = self._post_service.update_caption(post=post, caption=input_dto.caption)
        if not result.success or result.post is None:
            return UpdatePostOutput(success=False, error=result.error)
        return UpdatePostOutput(success=True, post=result.post)
