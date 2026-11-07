"""Services for the social domain (design decision 2): follow operations
and feed/suggestion retrieval on models, called by use cases."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import MAX_PAGINATION_BOUND
from apps.social.models import Follow

# Reference error strings (design decision 1): the service checks return
# these before the DB constraints (unique pair, no_self_follow) act as the
# backstop; a constraint hit that slips past the checks (concurrent racer)
# is translated into the same reference error (design decision 5), never a
# raw IntegrityError/500.
SELF_FOLLOW_ERROR = "You cannot follow yourself"
ALREADY_FOLLOWING_ERROR = "Already following this user"
FOLLOW_NOT_FOUND_ERROR = "Follow relationship not found"

# Up to 5 suggested accounts on the home page (spec: User suggestions).
SUGGESTIONS_LIMIT = 5


class FollowService:
    """Domain operations for the follow relationship (called by use cases)."""

    def follow(self, follower: User, following: User) -> Follow:
        """Create the follow relationship ``follower -> following``.

        Self-follows and duplicate pairs are rejected with the reference
        error strings (spec scenarios: Self-follow rejected, Duplicate
        follow rejected). When two concurrent racers both pass the
        ``is_following`` check, the database unique constraint rejects the
        loser's INSERT and the service translates that ``IntegrityError``
        into the same reference error, so the losing racer gets the
        reference toast instead of a 500 (design decision 5). The
        self-follow branch above is synchronous, so a self-follow can
        never reach the database constraint.
        """
        if follower.pk == following.pk:
            raise ValidationError(SELF_FOLLOW_ERROR)
        if self.is_following(follower, following):
            raise ValidationError(ALREADY_FOLLOWING_ERROR)
        try:
            return Follow.objects.create(follower=follower, following=following)
        except IntegrityError as exc:
            raise ValidationError(ALREADY_FOLLOWING_ERROR) from exc

    def unfollow(self, follower: User, following: User) -> None:
        """Remove the follow relationship ``follower -> following``.

        An unknown relationship is rejected with the reference error string
        (spec scenario: Web follow failure shows the cause — the failure
        reason is the message the UI surfaces).
        """
        deleted, _ = Follow.objects.filter(follower=follower, following=following).delete()
        if not deleted:
            raise ValidationError(FOLLOW_NOT_FOUND_ERROR)

    def is_following(self, follower: User, following: User) -> bool:
        """Return whether ``follower`` follows ``following``."""
        return Follow.objects.filter(follower=follower, following=following).exists()

    def get_following(self, user: User, *, q: str | None = None) -> list[User]:
        """Return the users ``user`` follows, newest relationship first.

        When ``q`` is given, only the followed users whose username, first
        name or last name matches it (case-insensitive) are returned — the
        search is a query concern that lives in the service (design decision
        9). The match is LITERAL (design decision 6): ``icontains`` on a
        direct value escapes ``%``, ``_`` and ``\\`` through the ORM's
        ``PatternLookup`` (``prep_for_like_query``), so wildcards never
        widen the match. Do NOT escape ``q`` here by hand — the ORM would
        escape it a second time and plain substrings containing those
        characters would stop matching. The followed users are loaded up
        front (``select_related``) so callers never trigger extra queries;
        ordering comes from the model's ``Meta.ordering``
        (``["-created_at"]``).
        """
        follows = Follow.objects.filter(follower=user).select_related("following")
        if q:
            follows = follows.filter(
                Q(following__username__icontains=q)
                | Q(following__first_name__icontains=q)
                | Q(following__last_name__icontains=q)
            )
        return [follow.following for follow in follows]

    def get_followers(self, user: User) -> list[User]:
        """Return the users following ``user``, newest relationship first."""
        follows = Follow.objects.filter(following=user).select_related("follower")
        return [follow.follower for follow in follows]


class FeedService:
    """Domain operations for the followed-users feed and suggestions
    (called by use cases)."""

    def list_feed(self, user: User, *, limit: int = 10, offset: int = 0) -> list[Post]:
        """Return the posts of the users ``user`` follows, newest first.

        A subquery on ``Follow`` selects the posts whose owner is followed
        (reference pattern, design decision 2); the user's own posts are not
        included (self-follow is forbidden by the model). Ordering is
        newest first with the identifier as tiebreaker
        (``["-created_at", "-id"]``, design decision 2, kept consistent with
        ``Post.Meta.ordering`` and ``PostService.list_for_user``), so
        pagination windows stay deterministic. ``limit``/``offset`` slice
        the window without duplicates across pages; values beyond
        ``MAX_PAGINATION_BOUND`` are clamped exactly as in ``PostService`` so
        an unbounded integer never overflows the database binding.
        """
        limit = min(limit, MAX_PAGINATION_BOUND)
        offset = min(offset, MAX_PAGINATION_BOUND)
        followed_ids = Follow.objects.filter(follower=user).values("following")
        return list(
            Post.objects.filter(owner__in=followed_ids)
            .select_related("owner")
            .order_by("-created_at", "-id")[offset : offset + limit]
        )

    def get_suggestions(self, user: User, *, limit: int = SUGGESTIONS_LIMIT) -> list[User]:
        """Return up to ``limit`` suggested accounts for ``user``.

        Suggestions never contain the user themselves nor anyone they
        already follow (spec scenarios: Suggestions exclude followed users
        and self) and are capped to the newest accounts, ordered by
        ``-date_joined`` (spec scenario: Suggestions limited to newest
        accounts).
        """
        followed_ids = Follow.objects.filter(follower=user).values("following")
        return list(
            User.objects.exclude(pk=user.pk)
            .exclude(pk__in=followed_ids)
            .order_by("-date_joined")[:limit]
        )
