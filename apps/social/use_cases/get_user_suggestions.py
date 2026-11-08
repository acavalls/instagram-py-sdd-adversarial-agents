from dataclasses import dataclass

from apps.accounts.models import User
from apps.social.services import SUGGESTIONS_LIMIT, FeedService


@dataclass(frozen=True, slots=True)
class GetUserSuggestionsInput:
    """Suggestions request submitted by an adapter (web view)."""

    user: User
    limit: int = SUGGESTIONS_LIMIT


@dataclass(frozen=True, slots=True)
class GetUserSuggestionsOutput:
    """The suggested users for the requester, newest accounts first."""

    success: bool
    suggestions: list[User]
    error: str | None = None


class GetUserSuggestionsUseCase:
    """Suggest up to `limit` accounts the requester does not follow.

    Self and followed users are excluded below this layer (service);
    this use case only forwards the input and reports the suggestion
    list the adapters render in the sidebar column.
    """

    def __init__(self, feed_service: FeedService) -> None:
        self._feed_service = feed_service

    def execute(self, input_dto: GetUserSuggestionsInput) -> GetUserSuggestionsOutput:
        suggestions = self._feed_service.get_suggestions(input_dto.user, limit=input_dto.limit)
        return GetUserSuggestionsOutput(success=True, suggestions=suggestions)
