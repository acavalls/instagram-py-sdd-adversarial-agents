"""Web profile page tests for the social capability, named after the spec
scenarios they cover (task group 6): the profile stats row, the owner's
editable grid, the visitor's follow state, the 404 for unknown identifiers
and the pagination window (social spec: User profile page)."""

import uuid
from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.posts.models import Post
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


def make_post(owner: User, caption: str, created_at: str | None = None) -> Post:
    post = Post.objects.create(owner=owner, caption=caption)
    if created_at is not None:
        Post.objects.filter(pk=post.pk).update(created_at=created_at)
    return post


def follow(follower: User, following: User) -> None:
    FollowService().follow(follower=follower, following=following)


def profile_url(user: User) -> str:
    return f"/web/profile/{user.pk}/"


def get_profile(client: Client, viewer: User | None, target: User):
    if viewer is not None:
        client.force_login(viewer)
    return client.get(profile_url(target))


# --- Spec scenario: Own profile shows stats and editable grid ----------------


def test_own_profile_shows_stats_and_editable_grid(client):
    """Spec scenario: Own profile shows stats and editable grid — the owner
    sees the posts/followers/following counters and the edit and delete
    controls on their own posts (no follow button on their own profile)."""
    user = make_user()
    follower = make_user("bob")
    followed = make_user("carol")
    follow(follower, user)  # one follower of the profile owner
    follow(user, followed)  # the owner follows one account
    make_post(user, "first own post", "2024-01-01T10:00:00Z")
    make_post(user, "second own post", "2024-06-01T10:00:00Z")

    response = get_profile(client, user, user)

    assert response.status_code == 200
    content = response.content.decode()
    # The grid shows the owner's posts, newest first.
    assert "first own post" in content
    assert "second own post" in content
    assert content.index("second own post") < content.index("first own post")
    # The stats row shows the counters: 2 posts, 1 follower, 1 following.
    assert 'id="stat-posts">2<' in content
    assert 'id="stat-followers">1<' in content
    # The following counter renders as the (placeholder) modal trigger link.
    assert 'id="following-count-link"' in content
    assert 'stat-value">1<' in content  # the following count inside the link
    # Editable grid: the shared card renders the edit/delete controls.
    assert "post-actions" in content
    assert "Delete this post?" in content
    # No follow button on the owner's own profile (the class names also live
    # in the base stylesheet, so the check is on the rendered buttons).
    assert ">Follow</button>" not in content
    assert ">Following</button>" not in content
    assert 'hx-post="/web/follow/' not in content


def test_other_profile_grid_has_no_edit_controls(client):
    """A visitor never sees edit/delete controls on another user's posts;
    the shared card renders without them (the controls are owner-only)."""
    owner = make_user()
    visitor = make_user("visitor")
    make_post(owner, "bob caption post")

    response = get_profile(client, visitor, owner)

    assert response.status_code == 200
    content = response.content.decode()
    assert "bob caption post" in content
    # The class name also lives in the stylesheet, so the check is on the
    # rendered edit/delete controls: none of them exist on a visitor's grid.
    assert ">Edit</button>" not in content
    assert ">Delete</button>" not in content
    assert "Delete this post?" not in content
    assert "/edit-form/" not in content


# --- Spec scenario: Other user profile shows stats and follow state ----------


def test_other_profile_shows_follow_button_for_new_visitor(client):
    """Spec scenario: Other user profile shows stats and follow state — a
    visitor who does not follow the profile owner sees the follow button
    posting to the follow URL, and the profile's posts and counters."""
    owner = make_user()
    visitor = make_user("visitor")
    make_post(owner, "owner post", "2024-03-01T10:00:00Z")
    make_user("stranger")  # an extra account that neither follows anybody

    response = get_profile(client, visitor, owner)

    assert response.status_code == 200
    content = response.content.decode()
    assert "owner post" in content
    assert 'id="stat-posts">1<' in content
    assert 'id="stat-followers">0<' in content
    # Follow state: the button offers to follow the profile owner.
    assert "follow-button" in content
    assert ">Follow</button>" in content
    assert f'hx-post="/web/follow/{owner.pk}/"' in content


def test_other_profile_shows_following_state_when_already_following(client):
    """Spec scenario: Other user profile shows stats and follow state — when
    the visitor already follows the profile owner the button reflects the
    following state (it posts to the unfollow URL)."""
    owner = make_user()
    visitor = make_user("visitor")
    follow(visitor, owner)

    response = get_profile(client, visitor, owner)

    assert response.status_code == 200
    content = response.content.decode()
    assert "follow-button-following" in content
    assert ">Following</button>" in content
    assert f'hx-post="/web/unfollow/{owner.pk}/"' in content
    assert 'id="stat-followers">1<' in content


# --- Spec scenario: Unknown profile responds 404 -----------------------------


def test_unknown_profile_responds_404(client):
    """Spec scenario: Unknown profile responds 404 — a well-formed but
    non-existent identifier answers 404."""
    viewer = make_user()

    response = _get_unknown(client, viewer)

    assert response.status_code == 404


def _get_unknown(client: Client, viewer: User):
    client.force_login(viewer)
    return client.get(f"/web/profile/{uuid.uuid4()}/")


def test_profile_requires_login(client):
    """An anonymous visitor is redirected to the login page instead of
    seeing any profile (design decision 7: protected pages require login)."""
    target = make_user()

    response = client.get(profile_url(target))

    assert response.status_code == 302
    assert "/web/login/" in response.url


# --- Grid pagination ----------------------------------------------------------


def test_profile_grid_paginates_in_windows_of_twelve(client):
    """The profile grid paginates the owner's posts newest first: the first
    page shows the 12 newest and offers Next, the second page shows the
    remaining (oldest) post without duplicates."""
    owner = make_user()
    visitor = make_user("visitor")
    for index in range(13):  # 13 posts: 12 on page 1, 1 on page 2
        make_post(owner, f"post number {index}", f"2024-01-{index + 1:02d}T10:00:00Z")

    client.force_login(visitor)
    first_page = client.get(profile_url(owner))
    second_page = client.get(f"{profile_url(owner)}?page=2")

    assert first_page.status_code == 200
    first_content = first_page.content.decode()
    # Newest first: post 12 (January 13th) opens the grid, post 0 is cut.
    assert "post number 12" in first_content
    assert "post number 1" in first_content
    assert "post number 0" not in first_content
    assert '<article class="post-card"' in first_content
    assert first_content.count("<article class=") == 12
    assert 'href="?page=2"' in first_content  # Next link
    assert 'href="?page=0"' not in first_content

    assert second_page.status_code == 200
    second_content = second_page.content.decode()
    assert "post number 0" in second_content  # the oldest post
    assert "post number 12" not in second_content  # no duplicates across pages
    assert 'href="?page=1"' in second_content  # Previous link
    assert 'href="?page=3"' not in second_content  # no Next past the last page


def test_profile_invalid_page_param_falls_back_to_first_page(client):
    """A missing or non-numeric page parameter falls back to page 1 (same
    edge rule as the home feed, design decision 4)."""
    owner = make_user()
    visitor = make_user("visitor")
    make_post(owner, "the only post")

    client.force_login(visitor)
    response = client.get(f"{profile_url(owner)}?page=not-a-number")

    assert response.status_code == 200
    content = response.content.decode()
    assert "the only post" in content
    assert "Page 1" in content
