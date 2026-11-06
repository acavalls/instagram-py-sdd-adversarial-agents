"""Use cases for the posts domain (application layer)."""

import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import File

from apps.accounts.models import User
from apps.posts.models import CAPTION_TOO_LONG_ERROR, Post
from apps.posts.services import PostService

# Spec error for an unknown post identifier (delta spec: Post detail —
# "Unknown post detail" expects exactly this message, mapped to 404).
POST_NOT_FOUND_ERROR = "Post not found"


@dataclass(frozen=True, slots=True)
class CreatePostInput:
    """Input DTO for the post creation use case."""

    owner: User
    caption: str
    media_files: list[File] | None = None


@dataclass(frozen=True, slots=True)
class CreatePostOutput:
    """Output DTO for the post creation use case (errors as strings)."""

    success: bool
    post: Post | None = None
    error: str | None = None


class CreatePostUseCase:
    """Create a post for a user with optional media files."""

    def __init__(self, post_service: PostService | None = None) -> None:
        self._post_service = post_service or PostService()

    def execute(self, input_dto: CreatePostInput) -> CreatePostOutput:
        """Create the post; a caption over the limit fails explicitly.

        The media count limit (up to 10) is enforced by the callers/
        serializers (design decision 5), not here.
        """
        try:
            post = self._post_service.create(
                owner=input_dto.owner,
                caption=input_dto.caption,
                media_files=input_dto.media_files,
            )
        except ValidationError:
            return CreatePostOutput(success=False, error=CAPTION_TOO_LONG_ERROR)
        return CreatePostOutput(success=True, post=post)


@dataclass(frozen=True, slots=True)
class ListPostsInput:
    """Input DTO for the post listing use case."""

    user: User
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListPostsOutput:
    """Output DTO for the post listing use case (newest first)."""

    success: bool
    posts: list[Post]


class ListPostsUseCase:
    """List the user's own posts with limit/offset pagination."""

    def __init__(self, post_service: PostService | None = None) -> None:
        self._post_service = post_service or PostService()

    def execute(self, input_dto: ListPostsInput) -> ListPostsOutput:
        """Return the user's own posts, newest first, paginated."""
        posts = self._post_service.list_for_user(
            input_dto.user, limit=input_dto.limit, offset=input_dto.offset
        )
        return ListPostsOutput(success=True, posts=posts)


@dataclass(frozen=True, slots=True)
class GetPostInput:
    """Input DTO for the post detail use case."""

    post_id: uuid.UUID | str
    user: User


@dataclass(frozen=True, slots=True)
class GetPostOutput:
    """Output DTO for the post detail use case (errors as strings)."""

    success: bool
    post: Post | None = None
    error: str | None = None


class GetPostUseCase:
    """Retrieve a single post by identifier, enforcing ownership."""

    def __init__(self, post_service: PostService | None = None) -> None:
        self._post_service = post_service or PostService()

    def execute(self, input_dto: GetPostInput) -> GetPostOutput:
        """Return the post when the user owns it, or the spec error otherwise.

        Posts are visible only through their owner's content listings (delta
        spec: Post visibility), so a non-owner gets the same "Post not
        found" error as an unknown id — never the post.
        """
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None or not self._post_service.is_owner(post, input_dto.user):
            return GetPostOutput(success=False, error=POST_NOT_FOUND_ERROR)
        return GetPostOutput(success=True, post=post)


@dataclass(frozen=True, slots=True)
class UpdatePostInput:
    """Input DTO for the caption update use case."""

    post_id: uuid.UUID | str
    user: User
    caption: str


@dataclass(frozen=True, slots=True)
class UpdatePostOutput:
    """Output DTO for the caption update use case (errors as strings)."""

    success: bool
    post: Post | None = None
    error: str | None = None


class UpdatePostUseCase:
    """Update a post's caption, enforcing ownership via the model."""

    def __init__(self, post_service: PostService | None = None) -> None:
        self._post_service = post_service or PostService()

    def execute(self, input_dto: UpdatePostInput) -> UpdatePostOutput:
        """Update the caption when the user owns the post.

        Unknown id → ``POST_NOT_FOUND_ERROR`` (mapped to 404); non-owner →
        the model's ``can_edit`` error (mapped to 403), design decision 2.
        """
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None:
            return UpdatePostOutput(success=False, error=POST_NOT_FOUND_ERROR)
        allowed, error = Post.can_edit(post, input_dto.user)
        if not allowed:
            return UpdatePostOutput(success=False, error=error)
        updated_post = self._post_service.update_caption(post, input_dto.caption)
        return UpdatePostOutput(success=True, post=updated_post)


@dataclass(frozen=True, slots=True)
class DeletePostInput:
    """Input DTO for the post deletion use case."""

    post_id: uuid.UUID | str
    user: User


@dataclass(frozen=True, slots=True)
class DeletePostOutput:
    """Output DTO for the post deletion use case (errors as strings)."""

    success: bool
    error: str | None = None


class DeletePostUseCase:
    """Delete a post (media cascade with it), enforcing ownership."""

    def __init__(self, post_service: PostService | None = None) -> None:
        self._post_service = post_service or PostService()

    def execute(self, input_dto: DeletePostInput) -> DeletePostOutput:
        """Delete the post when the user owns it.

        Unknown id → ``POST_NOT_FOUND_ERROR`` (mapped to 404); non-owner →
        the model's ``can_delete`` error (mapped to 403), design decision 2.
        """
        post = self._post_service.get_by_id(input_dto.post_id)
        if post is None:
            return DeletePostOutput(success=False, error=POST_NOT_FOUND_ERROR)
        allowed, error = Post.can_delete(post, input_dto.user)
        if not allowed:
            return DeletePostOutput(success=False, error=error)
        self._post_service.delete(post)
        return DeletePostOutput(success=True)
