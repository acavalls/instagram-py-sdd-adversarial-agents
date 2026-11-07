"""Use case tests for the social domain (tasks 2.2 and 3.2), named after the
spec scenarios they back at the use case level."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow
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

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "sup3r-secret-pw",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_post(owner, caption="hello world", *, minutes_ago=0):
    """Create a post with a deterministic ``created_at`` (newest = smallest
    ``minutes_ago``) so ordering assertions never rely on clock speed."""
    post = Post.objects.create(owner=owner, caption=caption)
    Post.objects.filter(pk=post.pk).update(
        created_at=timezone.now() - timedelta(minutes=minutes_ago)
    )
    return Post.objects.get(pk=post.pk)


def test_follow_user_success():
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")

    output = FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=bob))

    assert output.success is True
    assert output.error is None
    assert output.follow is not None
    assert output.follow.follower == alice
    assert output.follow.following == bob


def test_self_follow_rejected():
    """Scenario: Self-follow rejected (use case level) — the exact reference
    error string is surfaced and nothing is stored."""
    alice = make_user()

    output = FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=alice))

    assert output.success is False
    assert output.follow is None
    assert output.error == "You cannot follow yourself"
    assert not Follow.objects.exists()


def test_duplicate_follow_rejected():
    """Scenario: Duplicate follow rejected (use case level) — the exact
    reference error string is surfaced and the original relationship stays."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    use_case = FollowUserUseCase()
    use_case.execute(FollowUserInput(user=alice, target_user=bob))

    output = use_case.execute(FollowUserInput(user=alice, target_user=bob))

    assert output.success is False
    assert output.follow is None
    assert output.error == "Already following this user"
    assert Follow.objects.count() == 1


def test_unfollow_user_success():
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=bob))

    output = UnfollowUserUseCase().execute(UnfollowUserInput(user=alice, target_user=bob))

    assert output.success is True
    assert output.error is None
    assert not Follow.objects.exists()


def test_unfollow_unknown_relationship_reports_not_found():
    """Scenario: Web follow failure shows the cause (use case level) — an
    unfollow of a relationship that does not exist surfaces the exact
    reference error string the UI shows in the error toast."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")

    output = UnfollowUserUseCase().execute(UnfollowUserInput(user=alice, target_user=bob))

    assert output.success is False
    assert output.error == "Follow relationship not found"


def test_list_feed_returns_followed_users_posts_newest_first():
    """Scenario: Feed shows followed users' posts (use case level) — the
    output contains only the followed users' posts, newest first."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=bob))
    FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=carol))
    bob_post = make_post(bob, caption="bob's post", minutes_ago=10)
    carol_post = make_post(carol, caption="carol's post", minutes_ago=5)
    make_post(dave, caption="stranger's post", minutes_ago=3)
    make_post(alice, caption="alice's own post", minutes_ago=1)

    output = ListFeedUseCase().execute(ListFeedInput(user=alice, limit=10, offset=0))

    assert output.success is True
    assert [post.pk for post in output.posts] == [carol_post.pk, bob_post.pk]


def test_list_feed_paginates_without_duplicates():
    """Scenario: Feed ordered newest first with pagination (use case level)
    — consecutive limit/offset windows tile the feed without repeats."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=bob))
    posts = [make_post(bob, caption=f"post {index}", minutes_ago=30 - index) for index in range(4)]

    page_one = ListFeedUseCase().execute(ListFeedInput(user=alice, limit=2, offset=0))
    page_two = ListFeedUseCase().execute(ListFeedInput(user=alice, limit=2, offset=2))

    assert [post.pk for post in page_one.posts] == [posts[3].pk, posts[2].pk]
    assert [post.pk for post in page_two.posts] == [posts[1].pk, posts[0].pk]
    page_pks = [post.pk for post in (*page_one.posts, *page_two.posts)]
    assert len(set(page_pks)) == len(page_pks) == 4


def test_get_suggestions_exclude_followed_users_and_self():
    """Scenario: Suggestions exclude followed users and self (use case
    level) — the panel output never contains the user themselves nor anyone
    they already follow."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    FollowUserUseCase().execute(FollowUserInput(user=alice, target_user=bob))

    output = GetUserSuggestionsUseCase().execute(GetUserSuggestionsInput(user=alice))

    assert output.success is True
    assert set(output.users) == {carol, dave}
    assert alice not in output.users
    assert bob not in output.users


def test_get_suggestions_limited_to_five_newest_accounts():
    """Scenario: Suggestions limited to newest accounts (use case level) —
    when more than 5 unfollowed users exist, only the 5 most recently
    joined accounts are suggested."""
    alice = make_user()
    base = timezone.now()
    users = []
    for index in range(6):
        user = make_user(username=f"user{index}", email=f"user{index}@example.com")
        User.objects.filter(pk=user.pk).update(date_joined=base - timedelta(days=index))
        users.append(user)

    output = GetUserSuggestionsUseCase().execute(GetUserSuggestionsInput(user=alice))

    assert output.success is True
    assert output.users == users[:5]
    assert len(output.users) == 5
