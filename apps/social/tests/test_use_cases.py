import pytest

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow
from apps.social.services import (
    ERROR_ALREADY_FOLLOWING,
    ERROR_FOLLOW_NOT_FOUND,
    ERROR_SELF_FOLLOW,
    FeedService,
    FollowService,
)
from apps.social.use_cases import (
    FollowUserInput,
    FollowUserUseCase,
    GetUserSuggestionsInput,
    GetUserSuggestionsUseCase,
    ListFeedInput,
    ListFeedUseCase,
    UnfollowUserInput,
    UnfollowUserUseCase,
)


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_post(owner: User, caption: str = "a post") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def _follow(follower: User, following: User):
    return FollowUserUseCase(FollowService()).execute(
        FollowUserInput(follower=follower, following=following)
    )


def _unfollow(follower: User, following: User):
    return UnfollowUserUseCase(FollowService()).execute(
        UnfollowUserInput(follower=follower, following=following)
    )


@pytest.mark.django_db
class TestFollowUserUseCase:
    def test_follow_success(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")

        output = _follow(follower, following)

        assert output.success and output.error is None
        assert output.follow is not None
        assert output.follow.follower == follower
        assert output.follow.following == following
        assert Follow.objects.count() == 1

    def test_self_follow_rejected(self) -> None:
        user = _make_user("alice")

        output = _follow(user, user)

        assert not output.success
        assert output.error == "You cannot follow yourself"
        assert output.error == ERROR_SELF_FOLLOW
        assert Follow.objects.count() == 0

    def test_duplicate_follow_rejected(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")
        _follow(follower, following)

        output = _follow(follower, following)

        assert not output.success
        assert output.error == "Already following this user"
        assert output.error == ERROR_ALREADY_FOLLOWING
        assert Follow.objects.count() == 1


@pytest.mark.django_db
class TestUnfollowUserUseCase:
    def test_unfollow_success(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")
        _follow(follower, following)

        output = _unfollow(follower, following)

        assert output.success and output.error is None
        assert Follow.objects.count() == 0

    def test_unfollow_unknown_relationship(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")

        output = _unfollow(follower, following)

        assert not output.success
        assert output.error == "Follow relationship not found"
        assert output.error == ERROR_FOLLOW_NOT_FOUND


@pytest.mark.django_db
class TestListFeedUseCase:
    def test_forwards_to_the_feed_service(self) -> None:
        viewer = _make_user("alice")
        followed = _make_user("bob")
        Follow.objects.create(follower=viewer, following=followed)
        post = _make_post(followed, caption="followed")

        output = ListFeedUseCase(FeedService()).execute(ListFeedInput(user=viewer))

        assert output.success and output.error is None
        assert [item.id for item in output.posts] == [post.id]
        assert output.follows_anyone is True

    def test_empty_feed_carries_the_empty_state_signal(self) -> None:
        lonely = _make_user("lonely")

        output = ListFeedUseCase(FeedService()).execute(ListFeedInput(user=lonely))

        assert output.success
        assert output.posts == []
        assert output.follows_anyone is False

    def test_pagination_arguments_are_forwarded(self) -> None:
        viewer = _make_user("alice")
        followed = _make_user("bob")
        Follow.objects.create(follower=viewer, following=followed)
        posts = [_make_post(followed, caption=f"post {i}") for i in range(4)]
        newest_first = [post.id for post in reversed(posts)]

        output = ListFeedUseCase(FeedService()).execute(
            ListFeedInput(user=viewer, limit=2, offset=2)
        )

        assert [item.id for item in output.posts] == newest_first[2:4]


@pytest.mark.django_db
class TestGetUserSuggestionsUseCase:
    def test_forwards_to_the_feed_service(self) -> None:
        viewer = _make_user("alice")
        followed = _make_user("bob")
        stranger = _make_user("carol")
        Follow.objects.create(follower=viewer, following=followed)

        output = GetUserSuggestionsUseCase(FeedService()).execute(
            GetUserSuggestionsInput(user=viewer)
        )

        assert output.success and output.error is None
        assert output.suggestions == [stranger]

    def test_limit_is_forwarded(self) -> None:
        viewer = _make_user("alice")
        for i in range(3):
            _make_user(f"member{i}")

        output = GetUserSuggestionsUseCase(FeedService()).execute(
            GetUserSuggestionsInput(user=viewer, limit=2)
        )

        assert len(output.suggestions) == 2
