from dataclasses import dataclass

from apps.accounts.models import User
from apps.posts.models import Story
from apps.posts.services import StoryService


@dataclass(frozen=True, slots=True)
class CreateStoryInput:
    """Story creation data submitted by an adapter (web view)."""

    user: User


@dataclass(frozen=True, slots=True)
class CreateStoryOutput:
    """Result of creating a story."""

    success: bool
    story: Story | None = None
    error: str | None = None


class CreateStoryUseCase:
    """Create a story for the submitting user with generated placeholder media.

    The media generation and the 24-hour lifetime invariant are enforced
    below this layer (service/model); this use case only forwards the
    validated input and reports the explicit error strings the adapters
    map to responses.
    """

    def __init__(self, story_service: StoryService) -> None:
        self._story_service = story_service

    def execute(self, input_dto: CreateStoryInput) -> CreateStoryOutput:
        result = self._story_service.create(owner=input_dto.user)
        if not result.success or result.story is None:
            return CreateStoryOutput(success=False, error=result.error)
        return CreateStoryOutput(success=True, story=result.story)
