"""Services for the posts domain (design decision 3): read/write operations
on posts and stories, called by use cases."""

import io
import random
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.posts.models import (
    MEDIA_MAX_COUNT,
    MEDIA_TOO_MANY_ERROR,
    MediaType,
    Post,
    PostMedia,
    Story,
    StoryView,
)
from apps.social.models import Follow

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


@dataclass(frozen=True, slots=True)
class ViewerStory:
    """A story decorated with the viewer's view state (design decision 2).

    ``is_viewed`` answers "has THIS viewer seen THIS story?" — the per-story
    flag the stories bar ring states and the group ordering are built on.
    """

    story: Story
    is_viewed: bool


@dataclass(frozen=True, slots=True)
class StoryGroup:
    """One followed owner's active stories for the stories bar (design
    decision 2): newest story first, plus the owner for the avatar/label."""

    owner: User
    stories: list[ViewerStory]

    @property
    def is_viewed(self) -> bool:
        """Group ring state: whether the viewer has seen the newest story.

        The bar ordering (spec: Stories bar ordering) partitions groups by
        their latest story's view state, so the group is "viewed" exactly
        when its newest story is.
        """
        return bool(self.stories) and self.stories[0].is_viewed


def _build_placeholder_story_media() -> SimpleUploadedFile:
    """Build the generated placeholder story image (design decision 2).

    Same deterministic-media principle as the web post placeholder
    (``apps/web/post_views.py``), service-side: a random color in both the
    1x1 JPEG pixels and the filename so consecutive placeholder stories do
    not collide in the media storage.
    """
    color = random.randint(0, 0xFFFFFF)
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color).save(buffer, format="JPEG")
    return SimpleUploadedFile(
        f"story-{color:06x}.jpg", buffer.getvalue(), content_type="image/jpeg"
    )


class StoryService:
    """Domain operations for stories (called by use cases)."""

    def create(self, owner: User) -> Story:
        """Create a story for ``owner`` with the generated placeholder JPEG.

        The 24h expiration is set by ``Story.save`` on this path too
        (spec: Story data model — expiration exactly 24h after creation).
        """
        return Story.objects.create(owner=owner, image=_build_placeholder_story_media())

    def get_active_by_id(self, story_id: uuid.UUID | str) -> Story | None:
        """Return the non-expired story with the given id, or ``None``.

        Mirrors ``PostService.get_by_id`` with the story-active filter: an
        expired story is not active anywhere in the system (spec: Story data
        model), so callers get ``None`` exactly as for an unknown id — the
        owner is loaded up front (``select_related``) so use cases never
        trigger extra queries.
        """
        return (
            Story.objects.select_related("owner")
            .filter(pk=story_id, expires_at__gt=timezone.now())
            .first()
        )

    def get_active_for_user(self, owner: User) -> list[Story]:
        """Return ``owner``'s non-expired stories, newest first.

        An expired story is not active anywhere in the system (spec: Story
        data model), so the ``expires_at`` filter is the single source of
        the active/not-active decision; the model ordering
        (``["-created_at", "-id"]``) keeps the result deterministic.
        """
        return list(
            Story.objects.filter(owner=owner, expires_at__gt=timezone.now()).order_by(
                "-created_at", "-id"
            )
        )

    def get_feed_stories(self, viewer: User) -> list[StoryGroup]:
        """Return the active stories of the users ``viewer`` follows, grouped
        per owner for the stories bar (spec: Stories bar on the home page).

        ONLY followed users appear (spec: Bar excludes non-followed users) —
        the same ``Follow`` subquery pattern as ``FeedService.list_feed``.
        Each story carries the viewer's view state (spec: Story view
        tracking); groups whose newest story is unviewed come first,
        followed by viewed groups, and within each group the stories keep
        their creation order newest first (spec: Stories bar ordering).

        View state is one ``StoryView.exists`` query per story (design
        decision 2, matching the reference); acceptable at demo scale.
        """
        followed_ids = Follow.objects.filter(follower=viewer).values("following")
        stories = (
            Story.objects.filter(owner__in=followed_ids, expires_at__gt=timezone.now())
            .select_related("owner")
            .order_by("-created_at", "-id")
        )
        # Stories arrive newest first, so insertion order groups owners by
        # their newest story (most recent owner first).
        groups: dict[User, list[ViewerStory]] = {}
        for story in stories:
            viewed = ViewerStory(story=story, is_viewed=self.is_viewed(story, viewer))
            groups.setdefault(story.owner, []).append(viewed)
        result = [StoryGroup(owner=owner, stories=items) for owner, items in groups.items()]
        # Stable sort: unviewed groups first, recency order kept inside each
        # section (spec: Unviewed groups first).
        result.sort(key=lambda group: group.is_viewed)
        return result

    def is_viewed(self, story: Story, viewer: User) -> bool:
        """Return whether ``viewer`` has already viewed ``story``."""
        return StoryView.objects.filter(story=story, viewer=viewer).exists()

    def mark_viewed(self, story: Story, viewer: User) -> StoryView:
        """Record ``viewer``'s view of ``story`` exactly once (spec: Story
        view tracking — "Repeated view is idempotent").

        ``get_or_create`` is backed by the (story, viewer) unique constraint
        (design decision 1), so a repeated marking returns the existing
        record instead of duplicating it.
        """
        story_view, _created = StoryView.objects.get_or_create(story=story, viewer=viewer)
        return story_view

    def cleanup_expired(self) -> int:
        """Delete the expired stories and return how many were removed.

        ``StoryView`` rows cascade with their story via the FK
        ``on_delete=CASCADE`` (spec: Expired story cleanup — "deletes expired
        stories together with their view records"). The count is taken
        before the delete because Django's ``delete()`` return value counts
        the cascaded view records too, not just the stories.
        """
        expired = Story.objects.filter(expires_at__lte=timezone.now())
        count = expired.count()
        expired.delete()
        return count
