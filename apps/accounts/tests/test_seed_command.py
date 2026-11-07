"""Tests for the seed_demo_data management command (task 9.1, design
decision 11): the command builds the demo ecosystem through the existing
use cases/services and is idempotent on re-run. Story seeding follows design
decision 8 of change add-stories (one active story for some demo users)."""

from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia, Story
from apps.social.models import Follow

DEMO_USERNAMES = ["demoalice", "demobob", "democarol", "demodave", "demoerin"]
DEMO_FOLLOWS_COUNT = 8
DEMO_POSTS_COUNT = len(DEMO_USERNAMES) * 3
DEMO_PASSWORD = "demo-password-123"
DEMO_STORY_USERNAMES = ["demoalice", "demobob", "democarol"]
DEMO_STORIES_COUNT = len(DEMO_STORY_USERNAMES)


def test_seed_demo_data_creates_the_ecosystem(db):
    """Command run: users, follows among them and placeholder posts exist."""
    call_command("seed_demo_data")

    assert User.objects.filter(username__in=DEMO_USERNAMES).count() == len(DEMO_USERNAMES)
    assert (
        Follow.objects.filter(
            follower__username__in=DEMO_USERNAMES, following__username__in=DEMO_USERNAMES
        ).count()
        == DEMO_FOLLOWS_COUNT
    )
    assert Post.objects.filter(owner__username__in=DEMO_USERNAMES).count() == DEMO_POSTS_COUNT
    # Every demo post carries its generated placeholder media.
    assert (
        PostMedia.objects.filter(post__owner__username__in=DEMO_USERNAMES).count()
        == DEMO_POSTS_COUNT
    )
    # Alice follows Bob and Carol, so her feed is non-empty (spec: the seed
    # enables manual validation of the followed-users feed).
    alice = User.objects.get(username="demoalice")
    assert alice.following.count() == 2


def test_seed_demo_data_creates_active_stories(db):
    """Command run: one active story for each demo storyteller (design
    decision 8) — persisted with placeholder media and a future expiry, so
    the stories bar has data for manual validation."""
    call_command("seed_demo_data")

    stories = Story.objects.filter(owner__username__in=DEMO_STORY_USERNAMES)
    assert stories.count() == DEMO_STORIES_COUNT
    for story in stories:
        # generated placeholder JPEG
        assert story.image.name is not None and story.image.name.endswith(".jpg")
        assert story.expires_at > timezone.now()
        # Exactly the seeded creators authored stories (task: "some users").
        assert story.owner.username in DEMO_STORY_USERNAMES
        assert story.expires_at - story.created_at == timedelta(hours=24)


def test_seed_demo_data_stories_are_idempotent_on_rerun(db):
    """Re-running the command skips creation: no duplicate stories."""
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Story.objects.filter(owner__username__in=DEMO_STORY_USERNAMES).count() == (
        DEMO_STORIES_COUNT
    )


def test_seed_demo_data_is_idempotent_on_rerun(db, capsys):
    """Re-running the command skips creation: no duplicates anywhere."""
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert User.objects.filter(username__in=DEMO_USERNAMES).count() == len(DEMO_USERNAMES)
    assert (
        Follow.objects.filter(
            follower__username__in=DEMO_USERNAMES, following__username__in=DEMO_USERNAMES
        ).count()
        == DEMO_FOLLOWS_COUNT
    )
    assert Post.objects.filter(owner__username__in=DEMO_USERNAMES).count() == DEMO_POSTS_COUNT
    assert "skipping seed" in capsys.readouterr().out


def test_seed_demo_data_passwords_allow_login(db):
    """Demo users log in with the shared demo password (manual validation)."""
    call_command("seed_demo_data")

    for username in DEMO_USERNAMES:
        user = User.objects.get(username=username)
        assert user.check_password(DEMO_PASSWORD)


def test_seed_demo_data_uses_distinct_identities(db):
    """Each demo user has a distinct username and email (no partial seed)."""
    call_command("seed_demo_data")

    users = User.objects.filter(username__in=DEMO_USERNAMES)
    assert users.count() == len(DEMO_USERNAMES)
    assert len(set(users.values_list("username", flat=True))) == len(DEMO_USERNAMES)
    assert len(set(users.values_list("email", flat=True))) == len(DEMO_USERNAMES)
