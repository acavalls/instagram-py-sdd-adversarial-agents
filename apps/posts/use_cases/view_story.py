import uuid
from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Story
from apps.posts.services import StoryService
from apps.social.services.follow_service import FollowService

ERROR_STORY_NOT_FOUND = "Story not found"
ERROR_SELF_VIEW = "You cannot view your own story"
ERROR_NOT_FOLLOWING_OWNER = "You can only view stories from people you follow"


@dataclass(frozen=True, slots=True)
class ViewStoryInput:
    """Story view request submitted by an adapter (web view)."""

    story_id: uuid.UUID
    viewer: User


@dataclass(frozen=True, slots=True)
class ViewStoryOutput:
    """Result of viewing a story (or the reason it was rejected)."""

    success: bool
    story: Story | None = None
    error: str | None = None


class ViewStoryUseCase:
    """Record a view of a followed user's active story.

    Rejection rules (exact adapter-facing texts): an unknown or expired
    story identifier is "Story not found"; viewing one's own story is
    refused; stories of users the viewer does not follow are not
    viewable. A successful view records the (story, viewer) pair once.
    """

    def __init__(self, story_service: StoryService, follow_service: FollowService) -> None:
        self._story_service = story_service
        self._follow_service = follow_service

    def execute(self, input_dto: ViewStoryInput) -> ViewStoryOutput:
        story = self._story_service.get_active_by_id(input_dto.story_id)
        if story is None:
            return ViewStoryOutput(success=False, error=ERROR_STORY_NOT_FOUND)
        if story.owner_id == input_dto.viewer.pk:
            return ViewStoryOutput(success=False, story=story, error=ERROR_SELF_VIEW)
        if not self._follow_service.is_following(input_dto.viewer, story.owner):
            return ViewStoryOutput(success=False, story=story, error=ERROR_NOT_FOLLOWING_OWNER)
        self._story_service.mark_viewed(story, input_dto.viewer)
        return ViewStoryOutput(success=True, story=story)
