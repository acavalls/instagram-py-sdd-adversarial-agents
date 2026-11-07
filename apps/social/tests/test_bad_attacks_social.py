"""GBU adversarial attack tests for the social domain core (add-social
change, Bad iteration 1).

Attacks the service/use-case/management-command layer: duplicate and
self-follow sequences, unfollow-then-refollow churn, feed staleness after
unfollow, own-post leakage into the feed, pagination window integrity,
suggestion exclusion rules and seed_demo_data behavior on a dirty database.

Every test asserts behavior required by the social delta spec
(openspec/changes/add-social/specs/social/spec.md), so a failure is a
demonstrated defect.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

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

RAW_PASSWORD = "sup3r-secret-pw"


def make_user(username: str = "alice", **overrides) -> User:
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_post(owner: User, caption: str = "cap") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


# ---------------------------------------------------------------------------
# ATK-S01: follow error contract under hostile sequences
# ---------------------------------------------------------------------------


def test_atk_s01_self_follow_rejected_with_reference_error():
    alice = make_user("alice")
    with pytest.raises(ValidationError) as excinfo:
        FollowService().follow(alice, alice)
    assert SELF_FOLLOW_ERROR in str(excinfo.value)
    assert not Follow.objects.exists()


def test_atk_s02_duplicate_follow_rejected_and_no_second_row():
    alice, bob = make_user("alice"), make_user("bob")
    service = FollowService()
    service.follow(alice, bob)
    with pytest.raises(ValidationError) as excinfo:
        service.follow(alice, bob)
    assert ALREADY_FOLLOWING_ERROR in str(excinfo.value)
    assert Follow.objects.count() == 1


def test_atk_s03_unfollow_unknown_relationship_rejected():
    alice, bob = make_user("alice"), make_user("bob")
    with pytest.raises(ValidationError) as excinfo:
        FollowService().unfollow(alice, bob)
    assert FOLLOW_NOT_FOUND_ERROR in str(excinfo.value)


def test_atk_s04_follow_unfollow_refollow_churn_keeps_state_clean():
    """Churn: follow -> unfollow -> refollow must converge to exactly one
    row and correct counters (spec: Follow relationship data)."""
    alice, bob = make_user("alice"), make_user("bob")
    service = FollowService()
    service.follow(alice, bob)
    service.unfollow(alice, bob)
    service.follow(alice, bob)
    assert Follow.objects.count() == 1
    assert bob.followers.count() == 1
    assert alice.following.count() == 1


# ---------------------------------------------------------------------------
# ATK-S05: feed staleness and leakage
# ---------------------------------------------------------------------------


def test_atk_s05_unfollow_stale_feed_removed_immediately():
    """After an unfollow the followed user's posts must vanish from the
    feed on the very next read (no stale window)."""
    alice, bob = make_user("alice"), make_user("bob")
    post = make_post(bob, "bob post")
    service = FollowService()
    feed_service = FeedService()
    service.follow(alice, bob)
    assert post in feed_service.list_feed(alice)
    service.unfollow(alice, bob)
    assert feed_service.list_feed(alice) == []


def test_atk_s06_own_posts_never_leak_into_feed():
    alice, bob = make_user("alice"), make_user("bob")
    own = make_post(alice, "my own secret post")
    other = make_post(bob, "bob post")
    FollowService().follow(alice, bob)
    feed = FeedService().list_feed(alice)
    assert other in feed
    assert own not in feed


def test_atk_s07_followed_user_with_zero_posts_yields_empty_feed():
    alice, bob = make_user("alice"), make_user("bob")
    FollowService().follow(alice, bob)
    assert FeedService().list_feed(alice) == []


def test_atk_s08_feed_pagination_window_no_duplicates_no_gaps():
    """25 posts from a followed user, page size 12: pages 1..3 must cover
    every post exactly once (spec: pagination without duplicates)."""
    alice, bob = make_user("alice"), make_user("bob")
    FollowService().follow(alice, bob)
    posts = [make_post(bob, f"post {i}") for i in range(25)]
    feed_service = FeedService()
    window = (
        feed_service.list_feed(alice, limit=12, offset=0)
        + feed_service.list_feed(alice, limit=12, offset=12)
        + feed_service.list_feed(alice, limit=12, offset=24)
    )
    assert len(window) == 25
    assert {p.pk for p in window} == {p.pk for p in posts}
    assert len({p.pk for p in window}) == 25
    # Ordered newest first across the whole sequence.
    created = [p.created_at for p in window]
    assert created == sorted(created, reverse=True)


def test_atk_s09_feed_page_beyond_last_is_empty_not_error():
    alice, bob = make_user("alice"), make_user("bob")
    FollowService().follow(alice, bob)
    make_post(bob, "only post")
    assert FeedService().list_feed(alice, limit=12, offset=9999) == []


# ---------------------------------------------------------------------------
# ATK-S10: suggestions exclusion and refresh
# ---------------------------------------------------------------------------


def test_atk_s10_suggestions_exclude_self_followed_and_refresh_after_unfollow():
    service = FollowService()
    alice = make_user("alice")
    bob = make_user("bob")
    carol = make_user("carol")
    dave = make_user("dave")
    service.follow(alice, bob)
    feed_service = FeedService()
    suggestions = feed_service.get_suggestions(alice)
    assert set(u.pk for u in suggestions) == {carol.pk, dave.pk}
    assert alice.pk not in {u.pk for u in suggestions}
    # After unfollowing bob, bob re-enters the suggestion pool.
    service.unfollow(alice, bob)
    suggestions = feed_service.get_suggestions(alice)
    assert bob.pk in {u.pk for u in suggestions}


def test_atk_s11_suggestions_capped_to_five_newest():
    service = FollowService()
    alice = make_user("alice")
    for i in range(8):
        service.follow(alice, make_user(f"early{i}"))
    later = [make_user(f"late{i}") for i in range(7)]
    suggestions = FeedService().get_suggestions(alice)
    assert len(suggestions) == 5
    assert {u.pk for u in suggestions} == {u.pk for u in later[-5:]}


# ---------------------------------------------------------------------------
# ATK-S12: seed_demo_data on a dirty database
# ---------------------------------------------------------------------------


def test_atk_s12_seed_skips_without_crash_when_demo_username_preexists():
    """A real user already registered as 'demoalice' (different email) must
    not crash the seed nor duplicate the demo identity."""
    make_user("demoalice", email="real-person@example.com")
    call_command("seed_demo_data", stdout=None, verbosity=0)
    assert User.objects.filter(username="demoalice").count() == 1
    assert not User.objects.filter(username="demobob").exists()
    assert Follow.objects.count() == 0


def test_atk_s13_seed_idempotent_on_rerun():
    call_command("seed_demo_data", verbosity=0)
    users = User.objects.count()
    follows = Follow.objects.count()
    posts = Post.objects.count()
    call_command("seed_demo_data", verbosity=0)
    assert User.objects.count() == users
    assert Follow.objects.count() == follows
    assert Post.objects.count() == posts
