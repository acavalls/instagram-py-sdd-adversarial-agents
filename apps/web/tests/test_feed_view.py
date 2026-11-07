"""Web feed tests for the social capability, named after the spec scenarios
they cover (task group 4): the followed-users home feed and the suggestions
panel (social spec: Followed-users feed, User suggestions)."""

from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

FEED_URL = "/web/feed/"
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


# --- Spec scenario: Feed shows followed users' posts -------------------------


def test_feed_shows_followed_users_posts_as_cards(client):
    """Spec scenario: Feed shows followed users' posts — the home page shows
    only the followed users' posts as post cards (caption, owner,
    timestamp), ordered newest first; the user's own posts and unfollowed
    users' posts never appear."""
    user = make_user()
    followed_one = make_user("bob")
    followed_two = make_user("carol")
    stranger = make_user("dave")
    follow(user, followed_one)
    follow(user, followed_two)
    make_post(followed_one, "bob old post", "2024-01-01T10:00:00Z")
    make_post(followed_two, "carol new post", "2024-06-01T10:00:00Z")
    make_post(stranger, "dave hidden post", "2024-05-01T10:00:00Z")
    make_post(user, "alice own post", "2024-07-01T10:00:00Z")

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "bob old post" in content
    assert "carol new post" in content
    assert "dave hidden post" not in content
    assert "alice own post" not in content
    # Newest first: carol's June post before bob's January post.
    assert content.index("carol new post") < content.index("bob old post")
    # Rendered as post cards with the owner exposed.
    assert "post-card" in content
    assert "bob" in content
    assert "carol" in content


def _get_logged(client: Client, user: User):
    client.force_login(user)
    return client.get(FEED_URL)


# --- Spec scenario: Empty feed state -----------------------------------------


def test_empty_feed_state_when_following_nobody(client):
    """Spec scenario: Empty feed state — a logged-in user with no follows
    sees the empty state (pointing to the suggestions panel) instead of post
    cards, even when other users have posts."""
    user = make_user()
    other = make_user("bob")
    make_post(other, "bob invisible post")

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "bob invisible post" not in content
    assert '<article class="post-card"' not in content
    assert "feed-empty-state" in content
    assert "not following anyone" in content
    assert "suggestions" in content


def test_feed_without_follows_but_no_posts_shows_generic_empty_message(client):
    """A user who follows people whose accounts have no posts gets a feed
    without cards and the generic (non-empty-state) message."""
    user = make_user()
    followed = make_user("bob")
    follow(user, followed)

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert '<article class="post-card"' not in content
    assert "feed-empty-state" not in content  # the empty state is for no follows
    assert "No posts from the people you follow yet." in content


# --- Spec scenario: Suggestions exclude followed users and self --------------


def test_suggestions_panel_excludes_self_and_followed_users(client):
    """Spec scenario: Suggestions exclude followed users and self — the
    suggestions panel never contains the user themselves nor anyone they
    already follow; every other account is suggested, newest joined first."""
    user = make_user("alice", date_joined="2024-01-01T10:00:00Z")
    followed = make_user("bob", date_joined="2024-01-02T10:00:00Z")
    carol = make_user("carol", date_joined="2024-06-01T10:00:00Z")
    dave = make_user("dave", date_joined="2024-03-01T10:00:00Z")
    follow(user, followed)

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "@carol" in content
    assert "@dave" in content
    assert "@alice" not in content  # never the user themselves
    assert "@bob" not in content  # never anyone they already follow
    # Newest accounts first.
    assert content.index("@carol") < content.index("@dave")
    # Suggestions link to the suggested user's profile page (social spec:
    # User profile page).
    assert f'href="/web/profile/{carol.pk}/"' in content
    assert f'href="/web/profile/{dave.pk}/"' in content


def test_suggestions_panel_capped_at_five_newest_accounts(client):
    """Spec scenario: Suggestions limited to newest accounts (web path) —
    with more than 5 unfollowed users, only the 5 most recently joined
    accounts are suggested."""
    user = make_user("alice", date_joined="2024-01-01T10:00:00Z")
    for index in range(7):
        make_user(f"member{index}", date_joined=f"2024-02-{index + 1:02d}T10:00:00Z")

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    for index in range(2, 7):  # the 5 newest (February 3rd to 7th)
        assert f"@member{index}" in content
    for index in range(0, 2):  # the two oldest are cut
        assert f"@member{index}" not in content


def test_suggestions_panel_empty_when_everyone_is_followed(client):
    """With no suggestible accounts left the panel renders its empty message
    instead of entries (and the page still answers 200)."""
    user = make_user("alice")
    other = make_user("bob")
    follow(user, other)

    response = _get_logged(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "No suggestions right now." in content
