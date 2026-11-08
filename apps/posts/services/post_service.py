from dataclasses import dataclass

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.db import transaction

from apps.accounts.models import User
from apps.posts.models import ERROR_MEDIA_LIMIT_EXCEEDED, MEDIA_LIMIT, Post, PostMedia


@dataclass(frozen=True, slots=True)
class PostMediaInput:
    """One media file submitted for a new post (order assigned by position)."""

    file: File
    media_type: str


@dataclass(frozen=True, slots=True)
class CreatePostOutput:
    """Result of creating a post."""

    success: bool
    post: Post | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePostOutput:
    """Result of updating a post's caption."""

    success: bool
    post: Post | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DeletePostOutput:
    """Result of deleting a post (its media is removed with it)."""

    success: bool
    error: str | None = None


class PostService:
    """Domain service for post persistence and queries."""

    def get_by_id(self, post_id: object) -> Post | None:
        """Fetch a post by identifier with its owner and media loaded."""
        return (
            Post.objects.select_related("owner")
            .prefetch_related("media")
            .filter(pk=post_id)
            .first()
        )

    def list_for_user(
        self,
        user: AbstractBaseUser,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Post]:
        """List the user's own posts, newest first, in the requested window.

        The model's `Meta.ordering` (creation date descending, then
        identifier descending) provides the deterministic newest-first
        order; limit/offset carve the pagination window out of it.
        """
        queryset = Post.objects.filter(owner=user).select_related("owner")
        if offset:
            queryset = queryset[offset:]
        if limit is not None:
            queryset = queryset[:limit]
        return list(queryset)

    def exists(self, post_id: object) -> bool:
        """Whether a post with the identifier exists."""
        return Post.objects.filter(pk=post_id).exists()

    def is_owner(self, user: AbstractBaseUser, post: Post) -> bool:
        """Whether the user owns the post (delegates to the model rule)."""
        return post.can_edit(user)

    def create(
        self,
        *,
        user: User,
        caption: str,
        media: list[PostMediaInput] | tuple[PostMediaInput, ...] = (),
    ) -> CreatePostOutput:
        """Create a post with up to 10 media files.

        The media cap is refused here with an explicit error before any
        storage happens (the API scenario expects a 400 validation error,
        never a silent trim). The caption rule is enforced by the model
        on save; any model validation failure stores nothing.
        """
        if len(media) > MEDIA_LIMIT:
            return CreatePostOutput(success=False, error=ERROR_MEDIA_LIMIT_EXCEEDED)
        try:
            with transaction.atomic():
                post = Post(owner=user, caption=caption)
                post.save()
                PostMedia.objects.bulk_create(
                    PostMedia(
                        post=post,
                        file=item.file,
                        media_type=item.media_type,
                        order=position,
                    )
                    for position, item in enumerate(media)
                )
        except ValidationError as exc:
            return CreatePostOutput(success=False, error=self._first_error(exc))
        return CreatePostOutput(success=True, post=post)

    def update_caption(self, *, post: Post, caption: str) -> UpdatePostOutput:
        """Update a post's caption (the caption rule is enforced by the model)."""
        try:
            post.caption = caption
            post.save(update_fields=["caption", "updated_at"])
        except ValidationError as exc:
            return UpdatePostOutput(success=False, error=self._first_error(exc))
        return UpdatePostOutput(success=True, post=post)

    def delete(self, *, post: Post) -> DeletePostOutput:
        """Delete a post; its media rows are removed by the database cascade."""
        post.delete()
        return DeletePostOutput(success=True)

    @staticmethod
    def _first_error(exc: ValidationError) -> str:
        for message in exc.messages:
            if isinstance(message, str):
                return message
        return "Invalid data"
