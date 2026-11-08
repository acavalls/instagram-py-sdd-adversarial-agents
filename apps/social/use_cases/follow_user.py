from dataclasses import dataclass

from apps.accounts.models import User
from apps.social.models import Follow
from apps.social.services import FollowService


@dataclass(frozen=True, slots=True)
class FollowUserInput:
    """Follow request submitted by an adapter (web view)."""

    follower: User
    following: User


@dataclass(frozen=True, slots=True)
class FollowUserOutput:
    """Result of a follow request."""

    success: bool
    follow: Follow | None = None
    error: str | None = None


class FollowUserUseCase:
    """Follow another user on behalf of the requesting follower.

    The self-follow and duplicate rules are enforced below this layer
    (service/model); this use case only forwards the input and reports
    the explicit error strings the adapters map to responses.
    """

    def __init__(self, follow_service: FollowService) -> None:
        self._follow_service = follow_service

    def execute(self, input_dto: FollowUserInput) -> FollowUserOutput:
        result = self._follow_service.follow(
            follower=input_dto.follower,
            following=input_dto.following,
        )
        if not result.success or result.follow is None:
            return FollowUserOutput(success=False, error=result.error)
        return FollowUserOutput(success=True, follow=result.follow)
