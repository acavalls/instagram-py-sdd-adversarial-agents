from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.services import StoryFeedGroup, StoryService


@dataclass(frozen=True, slots=True)
class ListFeedStoriesInput:
    """Stories-bar listing request submitted by an adapter (web view)."""

    user: User


@dataclass(frozen=True, slots=True)
class ListFeedStoriesOutput:
    """The followed users' active story groups in bar order."""

    success: bool
    groups: list[StoryFeedGroup]
    error: str | None = None


class ListFeedStoriesUseCase:
    """List the stories-bar groups for the requesting user.

    Visibility rule: only the active stories of users the requester
    follows are reachable; other users' stories (and the requester's own)
    are excluded below this layer.
    """

    def __init__(self, story_service: StoryService) -> None:
        self._story_service = story_service

    def execute(self, input_dto: ListFeedStoriesInput) -> ListFeedStoriesOutput:
        groups = self._story_service.get_feed_stories(input_dto.user)
        return ListFeedStoriesOutput(success=True, groups=groups)
