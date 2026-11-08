import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

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


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _make_user_joined_on(username: str, date_joined) -> User:
    return User.objects.create(
        username=username, email=f"{username}@example.com", password="x", date_joined=date_joined
    )


def _make_post(owner: User, caption: str = "a post") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


class TestFollowServiceFollow:
    @pytest.mark.django_db
    def test_follow_persisted(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")

        output = FollowService().follow(follower=follower, following=following)

        assert output.success and output.error is None
        assert output.follow is not None
        assert isinstance(output.follow.id, uuid.UUID)
        assert output.follow.created_at is not None
        stored = Follow.objects.get(pk=output.follow.pk)
        assert stored.follower == follower
        assert stored.following == following

    @pytest.mark.django_db
    def test_self_follow_rejected(self) -> None:
        user = _make_user("alice")

        output = FollowService().follow(follower=user, following=user)

        assert not output.success
        assert output.error == ERROR_SELF_FOLLOW
        assert output.error == "You cannot follow yourself"
        assert Follow.objects.count() == 0

    @pytest.mark.django_db
    def test_duplicate_follow_rejected(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")
        FollowService().follow(follower=follower, following=following)

        output = FollowService().follow(follower=follower, following=following)

        assert not output.success
        assert output.error == ERROR_ALREADY_FOLLOWING
        assert output.error == "Already following this user"
        assert Follow.objects.count() == 1

    @pytest.mark.django_db
    def test_concurrent_duplicate_follow_maps_the_integrity_error(self) -> None:
        """A row inserted out of band (simulated concurrency) still maps
        to the friendly duplicate error via the IntegrityError catch."""
        follower = _make_user("alice")
        following = _make_user("bob")
        Follow.objects.create(follower=follower, following=following)

        output = FollowService().follow(follower=follower, following=following)

        assert not output.success
        assert output.error == "Already following this user"
        assert Follow.objects.count() == 1


class TestFollowServiceUnfollow:
    @pytest.mark.django_db
    def test_unfollow_removes_the_relationship(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")
        FollowService().follow(follower=follower, following=following)

        output = FollowService().unfollow(follower=follower, following=following)

        assert output.success and output.error is None
        assert Follow.objects.count() == 0

    @pytest.mark.django_db
    def test_unfollow_unknown_relationship(self) -> None:
        follower = _make_user("alice")
        following = _make_user("bob")

        output = FollowService().unfollow(follower=follower, following=following)

        assert not output.success
        assert output.error == ERROR_FOLLOW_NOT_FOUND
        assert output.error == "Follow relationship not found"


class TestFollowServiceQueries:
    @pytest.mark.django_db
    def test_is_following_reflects_the_relationship(self) -> None:
        service = FollowService()
        follower = _make_user("alice")
        following = _make_user("bob")
        other = _make_user("carol")

        assert service.is_following(follower, following) is False

        service.follow(follower=follower, following=following)

        assert service.is_following(follower, following) is True
        assert service.is_following(following, follower) is False
        assert service.is_following(follower, other) is False

    @pytest.mark.django_db
    def test_get_following_returns_the_followed_users(self) -> None:
        service = FollowService()
        alice = _make_user("alice")
        bob = _make_user("bob")
        carol = _make_user("carol")
        service.follow(follower=alice, following=bob)
        service.follow(follower=alice, following=carol)

        following = service.get_following(alice)

        assert following == [carol, bob]

    @pytest.mark.django_db
    def test_get_following_excludes_relationships_of_other_users(self) -> None:
        service = FollowService()
        alice = _make_user("alice")
        bob = _make_user("bob")
        carol = _make_user("carol")
        service.follow(follower=alice, following=carol)
        service.follow(follower=bob, following=carol)

        following = service.get_following(alice)

        assert following == [carol]

    @pytest.mark.django_db
    def test_get_followers_returns_the_follower_users(self) -> None:
        service = FollowService()
        alice = _make_user("alice")
        bob = _make_user("bob")
        carol = _make_user("carol")
        service.follow(follower=bob, following=alice)
        service.follow(follower=carol, following=alice)

        followers = service.get_followers(alice)

        assert followers == [carol, bob]


class TestFeedServiceListFeed:
    @pytest.mark.django_db
    def test_feed_shows_followed_users_posts(self) -> None:
        service = FeedService()
        viewer = _make_user("alice")
        followed = _make_user("bob")
        stranger = _make_user("carol")
        Follow.objects.create(follower=viewer, following=followed)
        followed_post = _make_post(followed, caption="followed")
        _make_post(stranger, caption="stranger's post")
        _make_post(viewer, caption="viewer's own post")

        page = service.list_feed(viewer)

        assert [post.id for post in page.posts] == [followed_post.id]
        assert page.posts[0].owner == followed
        assert page.follows_anyone is True

    @pytest.mark.django_db
    def test_feed_ordered_newest_first_with_pagination(self) -> None:
        service = FeedService()
        viewer = _make_user("alice")
        followed = _make_user("bob")
        Follow.objects.create(follower=viewer, following=followed)
        posts = [_make_post(followed, caption=f"post {i}") for i in range(5)]
        newest_first = [post.id for post in reversed(posts)]

        first = service.list_feed(viewer, limit=2, offset=0)
        second = service.list_feed(viewer, limit=2, offset=2)
        third = service.list_feed(viewer, limit=2, offset=4)

        assert [post.id for post in first.posts] == newest_first[0:2]
        assert [post.id for post in second.posts] == newest_first[2:4]
        assert [post.id for post in third.posts] == newest_first[4:5]
        window_ids = [post.id for post in first.posts + second.posts + third.posts]
        assert len(window_ids) == len(set(window_ids)) == 5

    @pytest.mark.django_db
    def test_feed_empty_state_cases(self) -> None:
        service = FeedService()
        lonely = _make_user("lonely")
        follower = _make_user("follower")
        quiet = _make_user("quiet")
        Follow.objects.create(follower=follower, following=quiet)

        no_follows = service.list_feed(lonely)
        assert no_follows.posts == []
        assert no_follows.follows_anyone is False

        follows_without_posts = service.list_feed(follower)
        assert follows_without_posts.posts == []
        assert follows_without_posts.follows_anyone is True


class TestFeedServiceSuggestions:
    @pytest.mark.django_db
    def test_suggestions_exclude_followed_users_and_self(self) -> None:
        service = FeedService()
        alice = _make_user("alice")
        bob = _make_user("bob")
        carol = _make_user("carol")
        dave = _make_user("dave")
        Follow.objects.create(follower=alice, following=bob)

        suggestions = service.get_suggestions(alice)

        assert set(suggestions) == {carol, dave}
        assert alice not in suggestions
        assert bob not in suggestions

    @pytest.mark.django_db
    def test_suggestions_limited_to_newest_accounts(self) -> None:
        service = FeedService()
        viewer = _make_user("viewer")
        base = timezone.now() - timedelta(days=10)
        oldest_first = [
            _make_user_joined_on(f"member{i}", base + timedelta(days=i)) for i in range(8)
        ]

        suggestions = service.get_suggestions(viewer)

        assert len(suggestions) == 5
        newest_first = [user.id for user in reversed(oldest_first)]
        assert [user.id for user in suggestions] == newest_first[:5]

    @pytest.mark.django_db
    def test_suggestions_limit_argument_is_honored(self) -> None:
        service = FeedService()
        viewer = _make_user("viewer")
        base = timezone.now() - timedelta(days=10)
        oldest_first = [
            _make_user_joined_on(f"member{i}", base + timedelta(days=i)) for i in range(3)
        ]

        suggestions = service.get_suggestions(viewer, limit=1)

        assert [user.id for user in suggestions] == [oldest_first[-1].id]
