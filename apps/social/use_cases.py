"""Use cases for the social domain (application layer)."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow
from apps.social.services import SUGGESTIONS_LIMIT, FeedService, FollowService


@dataclass(frozen=True, slots=True)
class FollowUserInput:
    """Input DTO for the follow use case."""

    user: User
    target_user: User


@dataclass(frozen=True, slots=True)
class FollowUserOutput:
    """Output DTO for the follow use case (errors as strings)."""

    success: bool
    follow: Follow | None = None
    error: str | None = None


class FollowUserUseCase:
    """Follow a user, surfacing the reference error strings on failure."""

    def __init__(self, follow_service: FollowService | None = None) -> None:
        self._follow_service = follow_service or FollowService()

    def execute(self, input_dto: FollowUserInput) -> FollowUserOutput:
        """Follow ``target_user`` on behalf of ``user``.

        Failures (self-follow, duplicate) return the reference error string
        so the web layer can show the failure cause (spec scenario: Web
        follow failure shows the cause).
        """
        try:
            follow = self._follow_service.follow(
                follower=input_dto.user, following=input_dto.target_user
            )
        except ValidationError as exc:
            return FollowUserOutput(success=False, error=exc.messages[0])
        return FollowUserOutput(success=True, follow=follow)


@dataclass(frozen=True, slots=True)
class UnfollowUserInput:
    """Input DTO for the unfollow use case."""

    user: User
    target_user: User


@dataclass(frozen=True, slots=True)
class UnfollowUserOutput:
    """Output DTO for the unfollow use case (errors as strings)."""

    success: bool
    error: str | None = None


class UnfollowUserUseCase:
    """Unfollow a user, surfacing the reference error strings on failure."""

    def __init__(self, follow_service: FollowService | None = None) -> None:
        self._follow_service = follow_service or FollowService()

    def execute(self, input_dto: UnfollowUserInput) -> UnfollowUserOutput:
        """Remove ``user``'s follow relationship with ``target_user``.

        An unknown relationship returns ``"Follow relationship not found"``
        (spec scenario: Web follow failure shows the cause).
        """
        try:
            self._follow_service.unfollow(follower=input_dto.user, following=input_dto.target_user)
        except ValidationError as exc:
            return UnfollowUserOutput(success=False, error=exc.messages[0])
        return UnfollowUserOutput(success=True)


@dataclass(frozen=True, slots=True)
class ListFeedInput:
    """Input DTO for the followed-users feed use case."""

    user: User
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ListFeedOutput:
    """Output DTO for the followed-users feed use case (newest first)."""

    success: bool
    posts: list[Post]


class ListFeedUseCase:
    """List the posts of the users the user follows (followed-users feed)."""

    def __init__(self, feed_service: FeedService | None = None) -> None:
        self._feed_service = feed_service or FeedService()

    def execute(self, input_dto: ListFeedInput) -> ListFeedOutput:
        """Return the followed users' posts, newest first, paginated.

        When the user follows nobody the result is simply empty — the empty
        state pointing to suggestions is a web-layer concern (task group 4).
        """
        posts = self._feed_service.list_feed(
            input_dto.user, limit=input_dto.limit, offset=input_dto.offset
        )
        return ListFeedOutput(success=True, posts=posts)


@dataclass(frozen=True, slots=True)
class GetUserSuggestionsInput:
    """Input DTO for the user suggestions use case."""

    user: User
    limit: int = SUGGESTIONS_LIMIT


@dataclass(frozen=True, slots=True)
class GetUserSuggestionsOutput:
    """Output DTO for the user suggestions use case (newest accounts first)."""

    success: bool
    users: list[User]


class GetUserSuggestionsUseCase:
    """Suggest up to 5 accounts the user does not follow, newest first."""

    def __init__(self, feed_service: FeedService | None = None) -> None:
        self._feed_service = feed_service or FeedService()

    def execute(self, input_dto: GetUserSuggestionsInput) -> GetUserSuggestionsOutput:
        """Return the suggestion panel accounts for ``user``.

        The result never contains the user themselves nor anyone they
        already follow, and is capped to the newest accounts (spec: User
        suggestions).
        """
        users = self._feed_service.get_suggestions(input_dto.user, limit=input_dto.limit)
        return GetUserSuggestionsOutput(success=True, users=users)
