"""Web follow/unfollow HTMX tests for the social capability, named after
the spec scenarios they cover (task group 5): the in-place button toggle
with its toast, and the failure path that keeps the state and shows the
cause (social spec: Follow and unfollow actions)."""

from typing import Any

import pytest

from apps.accounts.models import User
from apps.social.models import Follow
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


def make_user(username: str = "alice", **overrides: Any) -> User:
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def follow(follower: User, following: User) -> Follow:
    return FollowService().follow(follower=follower, following=following)


def follow_url(target: User) -> str:
    return f"/web/follow/{target.pk}/"


def unfollow_url(target: User) -> str:
    return f"/web/unfollow/{target.pk}/"


# --- Spec scenario: Web follow via HTMX --------------------------------------


def test_web_follow_via_htmx_toggles_to_following_with_success_toast(client):
    """Spec scenario: Web follow via HTMX — clicking the follow button stores
    the relationship, toggles the button to the following state (it now posts
    to the unfollow URL) and confirms with the "Followed successfully"
    toast."""
    viewer = make_user()
    target = make_user("bob")

    client.force_login(viewer)
    response = client.post(follow_url(target))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Followed successfully" in content
    # The button toggled to the following state.
    assert "follow-button-following" in content
    assert ">Following</button>" in content
    assert f'hx-post="{unfollow_url(target)}"' in content
    # The relationship is really stored.
    assert Follow.objects.filter(follower=viewer, following=target).exists()


def test_web_follow_requires_login(client):
    """An anonymous visitor is redirected to the login page instead of
    following anyone (user-accounts spec: Protected pages require login)."""
    target = make_user("bob")

    response = client.post(follow_url(target))

    assert response.status_code == 302
    assert "/web/login/" in response.url
    assert not Follow.objects.exists()


def test_web_follow_rejects_get_requests(client):
    """The follow action is POST-only (a state-changing action must not be
    triggerable by GET, same convention as the web logout)."""
    viewer = make_user()
    target = make_user("bob")

    client.force_login(viewer)
    response = client.get(follow_url(target))

    assert response.status_code == 405
    assert not Follow.objects.exists()


def test_web_follow_unknown_target_responds_404(client):
    """An unknown target identifier is an edge format rule: 404, like the
    profile page (design decision 8)."""
    viewer = make_user()

    client.force_login(viewer)
    response = client.post("/web/follow/00000000-0000-0000-0000-000000000000/")

    assert response.status_code == 404


# --- Spec scenario: Web unfollow via HTMX ------------------------------------


def test_web_unfollow_via_htmx_toggles_back_with_success_toast(client):
    """Spec scenario: Web unfollow via HTMX — clicking the following button
    removes the relationship, toggles the button back to the follow state
    (it now posts to the follow URL) and confirms with the "Unfollowed
    successfully" toast."""
    viewer = make_user()
    target = make_user("bob")
    follow(viewer, target)

    client.force_login(viewer)
    response = client.post(unfollow_url(target))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Unfollowed successfully" in content
    # The button toggled back to the follow state.
    assert "follow-button-following" not in content
    assert ">Follow</button>" in content
    assert f'hx-post="{follow_url(target)}"' in content
    # The relationship is really removed.
    assert not Follow.objects.filter(follower=viewer, following=target).exists()


def test_web_unfollow_requires_login(client):
    """An anonymous visitor is redirected to the login page instead of
    unfollowing anyone."""
    viewer = make_user()
    target = make_user("bob")
    follow(viewer, target)

    response = client.post(unfollow_url(target))

    assert response.status_code == 302
    assert "/web/login/" in response.url
    assert Follow.objects.filter(follower=viewer, following=target).exists()


def test_web_unfollow_unknown_target_responds_404(client):
    """An unknown target identifier answers 404, like the follow view."""
    viewer = make_user()

    client.force_login(viewer)
    response = client.post("/web/unfollow/00000000-0000-0000-0000-000000000000/")

    assert response.status_code == 404


# --- Spec scenario: Web follow failure shows the cause -----------------------


def test_web_follow_failure_duplicate_keeps_state_and_shows_cause(client):
    """Spec scenario: Web follow failure shows the cause (duplicate) —
    following an already-followed user keeps the following state (the button
    still posts to the unfollow URL) and an error toast shows the exact
    reference reason "Already following this user"; the relationship is
    untouched."""
    viewer = make_user()
    target = make_user("bob")
    follow(viewer, target)

    client.force_login(viewer)
    response = client.post(follow_url(target))

    assert response.status_code == 200
    content = response.content.decode()
    # The failure reason flows from the use-case output.
    assert "Already following this user" in content
    # The button keeps its current (following) state.
    assert "follow-button-following" in content
    assert f'hx-post="{unfollow_url(target)}"' in content
    # Exactly one relationship remains.
    assert Follow.objects.filter(follower=viewer, following=target).count() == 1


def test_web_follow_failure_self_follow_keeps_state_and_shows_cause(client):
    """Spec scenario: Web follow failure shows the cause (self-follow) — a
    crafted POST targeting the viewer's own identifier keeps the button in
    the follow state and the error toast shows "You cannot follow
    yourself"; no relationship is stored."""
    viewer = make_user()

    client.force_login(viewer)
    response = client.post(follow_url(viewer))

    assert response.status_code == 200
    content = response.content.decode()
    assert "You cannot follow yourself" in content
    # The button keeps its current (not following) state.
    assert "follow-button-following" not in content
    assert ">Follow</button>" in content
    assert not Follow.objects.exists()


def test_web_unfollow_failure_unknown_relationship_keeps_state_and_shows_cause(client):
    """Spec scenario: Web follow failure shows the cause (unknown
    relationship) — unfollowing a user that is not followed keeps the
    follow state and the error toast shows "Follow relationship not
    found"."""
    viewer = make_user()
    target = make_user("bob")

    client.force_login(viewer)
    response = client.post(unfollow_url(target))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Follow relationship not found" in content
    # The button keeps its current (follow) state.
    assert "follow-button-following" not in content
    assert ">Follow</button>" in content
    assert not Follow.objects.exists()
