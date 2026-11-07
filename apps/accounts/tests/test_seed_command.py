"""Tests for the seed_demo_data management command (task 9.1, design
decision 11): the command builds the demo ecosystem through the existing
use cases/services and is idempotent on re-run."""

from django.core.management import call_command

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia
from apps.social.models import Follow

DEMO_USERNAMES = ["demoalice", "demobob", "democarol", "demodave", "demoerin"]
DEMO_FOLLOWS_COUNT = 8
DEMO_POSTS_COUNT = len(DEMO_USERNAMES) * 3
DEMO_PASSWORD = "demo-password-123"


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
