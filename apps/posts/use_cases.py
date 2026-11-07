"""Use cases for the posts domain (application layer)."""

import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import File

from apps.accounts.models import User
from apps.posts.models import CAPTION_TOO_LONG_ERROR, Post, Story
from apps.posts.services import PostService, StoryGroup, StoryService
from apps.social.services import FollowService

# Spec error for an unknown post identifier (delta spec: Post detail —
# "Unknown post detail" expects exactly this message, mapped to 404).
POST_NOT_FOUND_ERROR = "Post not found"

# View-rule error strings (delta spec: Story view tracking; design decision
# 3). An unknown id and an expired story are indistinguishable for the
# viewer — an expired story "MUST NOT appear as active anywhere in the
# system" — so both report the plain not-found message.
STORY_NOT_FOUND_ERROR = "Story not found"
STORY_SELF_VIEW_ERROR = "You cannot view your own story"
STORY_NOT_FOLLOWED_ERROR = "You can only view stories from people you follow"


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


@dataclass(frozen=True, slots=True)
class CreateStoryInput:
    """Input DTO for the story creation use case."""

    owner: User


@dataclass(frozen=True, slots=True)
class CreateStoryOutput:
    """Output DTO for the story creation use case (errors as strings)."""

    success: bool
    story: Story | None = None
    error: str | None = None


class CreateStoryUseCase:
    """Create a story with the generated placeholder image (no upload).

    The media generation and the 24h expiration are service/model concerns
    (design decisions 1-2); the use case only orchestrates them.
    """

    def __init__(self, story_service: StoryService | None = None) -> None:
        self._story_service = story_service or StoryService()

    def execute(self, input_dto: CreateStoryInput) -> CreateStoryOutput:
        """Create the story for ``owner`` with a generated placeholder JPEG."""
        story = self._story_service.create(input_dto.owner)
        return CreateStoryOutput(success=True, story=story)


@dataclass(frozen=True, slots=True)
class ListFeedStoriesInput:
    """Input DTO for the feed-stories use case."""

    viewer: User


@dataclass(frozen=True, slots=True)
class ListFeedStoriesOutput:
    """Output DTO for the feed-stories use case (grouped, unviewed first)."""

    success: bool
    story_groups: list[StoryGroup]


class ListFeedStoriesUseCase:
    """Return the active stories of the users the viewer follows, grouped
    per owner for the stories bar."""

    def __init__(self, story_service: StoryService | None = None) -> None:
        self._story_service = story_service or StoryService()

    def execute(self, input_dto: ListFeedStoriesInput) -> ListFeedStoriesOutput:
        """Return the followed users' story groups (design decision 4).

        Follow filtering, view decoration and the unviewed-first ordering
        live in the service (design decision 2); the empty result is simply
        an empty list — the "Your story" add button is a template concern.
        """
        story_groups = self._story_service.get_feed_stories(input_dto.viewer)
        return ListFeedStoriesOutput(success=True, story_groups=story_groups)


@dataclass(frozen=True, slots=True)
class ViewStoryInput:
    """Input DTO for the story view use case."""

    story_id: uuid.UUID | str
    viewer: User


@dataclass(frozen=True, slots=True)
class ViewStoryOutput:
    """Output DTO for the story view use case (errors as strings)."""

    success: bool
    story: Story | None = None
    error: str | None = None


class ViewStoryUseCase:
    """Record the viewer's view of a followed user's active story.

    Design decision 3 (flagged deviation): the reference web view calls
    ``StoryService.mark_viewed`` directly; this project routes every write
    through a use case, which also enforces the delta's view rules the
    reference only partially enforces — no self-views, no non-followed
    stories, expired stories treated as not found.
    """

    def __init__(
        self,
        story_service: StoryService | None = None,
        follow_service: FollowService | None = None,
    ) -> None:
        self._story_service = story_service or StoryService()
        self._follow_service = follow_service or FollowService()

    def execute(self, input_dto: ViewStoryInput) -> ViewStoryOutput:
        """Record the view once, or reject with the rule's error string.

        Order of checks: unknown/expired id first (``STORY_NOT_FOUND_ERROR``),
        then self-view, then the follow relationship — the follow check is
        the only database query beyond the story fetch. A rejected input
        never records a ``StoryView`` (scenarios: Self-view rejected,
        Non-followed story not viewable); a repeated marking stays
        idempotent via the service (spec: Repeated view is idempotent).
        """
        story = self._story_service.get_active_by_id(input_dto.story_id)
        if story is None:
            return ViewStoryOutput(success=False, error=STORY_NOT_FOUND_ERROR)
        if story.owner_id == input_dto.viewer.pk:
            return ViewStoryOutput(success=False, error=STORY_SELF_VIEW_ERROR)
        if not self._follow_service.is_following(input_dto.viewer, story.owner):
            return ViewStoryOutput(success=False, error=STORY_NOT_FOLLOWED_ERROR)
        self._story_service.mark_viewed(story, input_dto.viewer)
        return ViewStoryOutput(success=True, story=story)
