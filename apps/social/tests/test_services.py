"""Service tests for the social domain (tasks 2.1 and 3.1), named after the
spec scenarios they back at the service level."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow
from apps.social.services import (
    ALREADY_FOLLOWING_ERROR,
    FOLLOW_NOT_FOUND_ERROR,
    SELF_FOLLOW_ERROR,
    FeedService,
    FollowService,
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


def follow(follower, following):
    FollowService().follow(follower=follower, following=following)


def test_self_follow_rejected():
    """Scenario: Self-follow rejected — the service refuses the relationship
    with the exact reference error string, and nothing is stored."""
    alice = make_user()

    with pytest.raises(ValidationError) as exc_info:
        FollowService().follow(follower=alice, following=alice)

    assert exc_info.value.messages == [SELF_FOLLOW_ERROR] == ["You cannot follow yourself"]
    assert not Follow.objects.exists()


def test_duplicate_follow_rejected():
    """Scenario: Duplicate follow rejected — the service refuses a second
    relationship for the same pair with the exact reference error string,
    and the original relationship is untouched."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    service = FollowService()
    service.follow(follower=alice, following=bob)

    with pytest.raises(ValidationError) as exc_info:
        service.follow(follower=alice, following=bob)

    assert exc_info.value.messages == [ALREADY_FOLLOWING_ERROR] == ["Already following this user"]
    assert Follow.objects.count() == 1


def test_follow_creates_relationship():
    """The service creates the relationship and reports it back."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")

    follow = FollowService().follow(follower=alice, following=bob)

    assert follow.follower == alice
    assert follow.following == bob
    assert Follow.objects.filter(follower=alice, following=bob).exists()


def test_unfollow_removes_relationship():
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    FollowService().follow(follower=alice, following=bob)

    FollowService().unfollow(follower=alice, following=bob)

    assert not Follow.objects.exists()


def test_unfollow_unknown_relationship_reports_not_found():
    """Scenario: Web follow failure shows the cause (unfollow of a
    relationship that does not exist) — the service reports the exact
    reference error string."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")

    with pytest.raises(ValidationError) as exc_info:
        FollowService().unfollow(follower=alice, following=bob)

    assert exc_info.value.messages == [FOLLOW_NOT_FOUND_ERROR] == ["Follow relationship not found"]


def test_is_following_reflects_the_relationship_state():
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    service = FollowService()

    assert service.is_following(alice, bob) is False
    service.follow(follower=alice, following=bob)
    assert service.is_following(alice, bob) is True
    assert service.is_following(bob, alice) is False
    service.unfollow(follower=alice, following=bob)
    assert service.is_following(alice, bob) is False


def test_get_following_returns_followed_users_newest_first():
    """The users a profile follows come back newest relationship first."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    service = FollowService()
    service.follow(follower=alice, following=bob)
    service.follow(follower=alice, following=carol)
    service.follow(follower=alice, following=dave)
    service.follow(follower=bob, following=alice)

    following = service.get_following(alice)

    assert following == [dave, carol, bob]


def test_get_following_search_filters_by_username_or_name():
    """The optional ``q`` search (design decision 9) keeps only the followed
    users whose username, first name or last name matches it
    case-insensitively; without ``q`` every followed user is returned."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com", first_name="Bob", last_name="Smith")
    carol = make_user(username="carol", email="carol@example.com", first_name="Carol")
    dave = make_user(username="dave", email="dave@example.com")
    service = FollowService()
    service.follow(follower=alice, following=bob)
    service.follow(follower=alice, following=carol)
    service.follow(follower=alice, following=dave)

    assert service.get_following(alice, q="dav") == [dave]
    assert service.get_following(alice, q="SMI") == [bob]
    assert service.get_following(alice, q="caro") == [carol]
    assert service.get_following(alice, q="zzz") == []
    assert service.get_following(alice) == [dave, carol, bob]


def test_get_followers_returns_follower_users_newest_first():
    """The users following a profile come back newest relationship first."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    service = FollowService()
    service.follow(follower=bob, following=alice)
    service.follow(follower=carol, following=alice)
    service.follow(follower=dave, following=alice)
    service.follow(follower=alice, following=bob)

    followers = service.get_followers(alice)

    assert followers == [dave, carol, bob]


def test_list_feed_returns_only_followed_users_posts():
    """Scenario: Feed shows followed users' posts — the feed contains only
    the posts of the users the logged-in user follows; their own posts and
    strangers' posts are never included."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    follow(alice, bob)
    follow(alice, carol)
    bob_post = make_post(bob, caption="bob's post", minutes_ago=10)
    carol_post = make_post(carol, caption="carol's post", minutes_ago=5)
    make_post(dave, caption="stranger's post", minutes_ago=3)
    make_post(alice, caption="alice's own post", minutes_ago=1)

    feed = FeedService().list_feed(alice, limit=10, offset=0)

    assert [post.pk for post in feed] == [carol_post.pk, bob_post.pk]
    assert all(post.owner in {bob, carol} for post in feed)


def test_list_feed_empty_when_following_nobody():
    """The feed of a user with no follows is empty (service level of the
    empty feed state; the web layer renders the empty state in task 4.1)."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    make_post(bob, caption="invisible to alice")

    assert FeedService().list_feed(alice, limit=10, offset=0) == []


def test_list_feed_pagination_window_no_duplicates_across_pages():
    """Scenario: Feed ordered newest first with pagination — limit/offset
    return exactly the requested window, newest first, without duplicates
    across pages."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    follow(alice, bob)
    posts = [make_post(bob, caption=f"post {index}", minutes_ago=60 - index) for index in range(5)]

    page_one = FeedService().list_feed(alice, limit=2, offset=0)
    page_two = FeedService().list_feed(alice, limit=2, offset=2)
    page_three = FeedService().list_feed(alice, limit=2, offset=4)

    assert [post.pk for post in page_one] == [posts[4].pk, posts[3].pk]
    assert [post.pk for post in page_two] == [posts[2].pk, posts[1].pk]
    assert [post.pk for post in page_three] == [posts[0].pk]
    # No duplicates across pages, and together the pages cover the feed.
    all_pks = [post.pk for post in (*page_one, *page_two, *page_three)]
    assert len(set(all_pks)) == len(all_pks) == 5
    # The owner is loaded up front (select_related) so post cards render
    # without extra queries.
    assert page_one[0].owner == bob


def test_get_suggestions_exclude_followed_users_and_self():
    """Scenario: Suggestions exclude followed users and self — the panel
    never contains the user themselves nor anyone they already follow."""
    alice = make_user()
    bob = make_user(username="bob", email="bob@example.com")
    carol = make_user(username="carol", email="carol@example.com")
    dave = make_user(username="dave", email="dave@example.com")
    follow(alice, bob)

    suggestions = FeedService().get_suggestions(alice)

    assert set(suggestions) == {carol, dave}
    assert alice not in suggestions
    assert bob not in suggestions


def test_get_suggestions_ordered_newest_accounts_first():
    """Suggestions come back newest accounts first (date_joined
    descending)."""
    base = timezone.now()
    alice = make_user()
    User.objects.filter(pk=alice.pk).update(date_joined=base)
    older = make_user(username="older", email="older@example.com")
    newer = make_user(username="newer", email="newer@example.com")
    User.objects.filter(pk=older.pk).update(date_joined=base - timedelta(days=10))
    User.objects.filter(pk=newer.pk).update(date_joined=base + timedelta(days=1))

    suggestions = FeedService().get_suggestions(alice)

    assert suggestions == [newer, older]


def test_get_suggestions_limited_to_five_newest_accounts():
    """Scenario: Suggestions limited to newest accounts — when more than 5
    unfollowed users exist, only the 5 most recently joined accounts are
    shown."""
    alice = make_user()
    base = timezone.now()
    users = []
    for index in range(6):
        user = make_user(username=f"user{index}", email=f"user{index}@example.com")
        User.objects.filter(pk=user.pk).update(date_joined=base - timedelta(days=index))
        users.append(user)

    suggestions = FeedService().get_suggestions(alice)

    # The 5 most recently joined, newest first; the oldest account is cut.
    assert suggestions == users[:5]
    assert len(suggestions) == 5
