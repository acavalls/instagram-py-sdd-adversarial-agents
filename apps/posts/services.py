"""Services for the posts domain (design decision 3): read/write operations
on posts, called by use cases."""

import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import File

from apps.accounts.models import User
from apps.posts.models import (
    MEDIA_MAX_COUNT,
    MEDIA_TOO_MANY_ERROR,
    MediaType,
    Post,
    PostMedia,
)

# Safe upper bound for limit/offset: the maximum SQLite INTEGER. Larger
# values overflow the database binding (IntegrityError), so they are clamped
# here — one guard for every caller (API views and the web feed), keeping
# the views thin (design decision 5) and the window semantics intact: an
# offset past the bound simply yields an empty window.
MAX_PAGINATION_BOUND = 2**63 - 1


class PostService:
    """Domain operations for posts (called by use cases)."""

    def get_by_id(self, post_id: uuid.UUID | str) -> Post | None:
        """Return the post with the given id, or ``None`` when unknown.

        The owner and the media are loaded up front (``select_related``/
        ``prefetch_related``) so callers never trigger extra queries.
        """
        return (
            Post.objects.select_related("owner")
            .prefetch_related("media")
            .filter(pk=post_id)
            .first()
        )

    def list_for_user(self, user: User, *, limit: int = 10, offset: int = 0) -> list[Post]:
        """Return the user's own posts, newest first, as a pagination window.

        Ordering is newest first with the identifier as tiebreaker (design
        decision 2: ``["-created_at", "-id"]``, kept consistent with
        ``Post.Meta.ordering`` and ``FeedService.list_feed``);
        ``limit``/``offset`` slice the window without duplicates across pages
        (spec: Post listing). Values beyond ``MAX_PAGINATION_BOUND`` are
        clamped so an unbounded integer never overflows the database binding.
        """
        limit = min(limit, MAX_PAGINATION_BOUND)
        offset = min(offset, MAX_PAGINATION_BOUND)
        return list(
            Post.objects.filter(owner=user).order_by("-created_at", "-id")[offset : offset + limit]
        )

    def exists(self, post_id: uuid.UUID | str) -> bool:
        """Return whether a post with the given id exists."""
        return Post.objects.filter(pk=post_id).exists()

    def is_owner(self, post: Post, user: User | None) -> bool:
        """Return whether ``user`` owns ``post`` (ownership lives on the
        model, design decision 2; this is the boolean convenience wrapper)."""
        allowed, _error = Post.can_edit(post, user)
        return allowed

    def create(
        self,
        owner: User,
        caption: str,
        media_files: list[File] | None = None,
    ) -> Post:
        """Create a post for ``owner`` and attach its media in order.

        ``media_files`` are uploaded-file-like objects (optional, up to 10 —
        design decision 3: the media-count invariant is enforced here too,
        because ``bulk_create`` bypasses ``PostMedia.save()``). Each file is
        persisted through ``bulk_create`` with its zero-based position, so
        ``PostMedia.order`` matches the submitted order. Returns the post
        (media attached afterwards, in a single bulk insert).
        """
        if media_files and len(media_files) > MEDIA_MAX_COUNT:
            raise ValidationError({"media": [MEDIA_TOO_MANY_ERROR]})
        post = Post.objects.create(owner=owner, caption=caption)
        if media_files:
            PostMedia.objects.bulk_create(
                PostMedia(
                    post=post,
                    image=media_file,
                    media_type=MediaType.IMAGE,
                    order=position,
                )
                for position, media_file in enumerate(media_files)
            )
        return post

    def update_caption(self, post: Post, caption: str) -> Post:
        """Update only the caption of ``post`` (and its ``updated_at``)."""
        post.caption = caption
        post.save(update_fields=["caption", "updated_at"])
        return post

    def delete(self, post: Post) -> None:
        """Delete ``post``; its media are removed by the database cascade."""
        post.delete()
