from dataclasses import dataclass

from apps.accounts.models import User
from apps.social.services import FollowService


@dataclass(frozen=True, slots=True)
class UnfollowUserInput:
    """Unfollow request submitted by an adapter (web view)."""

    follower: User
    following: User


@dataclass(frozen=True, slots=True)
class UnfollowUserOutput:
    """Result of an unfollow request."""

    success: bool
    error: str | None = None


class UnfollowUserUseCase:
    """Unfollow a user on behalf of the requesting follower.

    The unknown-relationship rule is enforced below this layer (service);
    this use case only forwards the input and reports the explicit error
    string the adapters map to responses.
    """

    def __init__(self, follow_service: FollowService) -> None:
        self._follow_service = follow_service

    def execute(self, input_dto: UnfollowUserInput) -> UnfollowUserOutput:
        result = self._follow_service.unfollow(
            follower=input_dto.follower,
            following=input_dto.following,
        )
        return UnfollowUserOutput(success=result.success, error=result.error)
