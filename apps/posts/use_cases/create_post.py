from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostMediaInput, PostService


@dataclass(frozen=True, slots=True)
class CreatePostInput:
    """Post creation data submitted by an adapter (web view or API)."""

    user: User
    caption: str
    media: tuple[PostMediaInput, ...] = ()


@dataclass(frozen=True, slots=True)
class CreatePostOutput:
    """Result of creating a post."""

    success: bool
    post: Post | None = None
    error: str | None = None


class CreatePostUseCase:
    """Create a post for the submitting user with up to 10 media files.

    The media cap and the caption rule are enforced below this layer
    (service/model); this use case only forwards the validated input and
    reports the explicit error strings the adapters map to responses.
    """

    def __init__(self, post_service: PostService) -> None:
        self._post_service = post_service

    def execute(self, input_dto: CreatePostInput) -> CreatePostOutput:
        result = self._post_service.create(
            user=input_dto.user,
            caption=input_dto.caption,
            media=input_dto.media,
        )
        if not result.success or result.post is None:
            return CreatePostOutput(success=False, error=result.error)
        return CreatePostOutput(success=True, post=result.post)
