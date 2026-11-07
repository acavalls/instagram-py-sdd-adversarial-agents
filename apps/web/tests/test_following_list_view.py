"""Web following-list modal tests for the social capability, named after
the spec scenarios they cover (task group 7): the list of users a profile
follows and the search filter (social spec: Following list)."""

import uuid
from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
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


def follow(follower: User, following: User) -> None:
    FollowService().follow(follower=follower, following=following)


def following_url(user: User) -> str:
    return f"/web/profile/{user.pk}/following/"


def get_following(client: Client, viewer: User, target: User, q: str | None = None):
    client.force_login(viewer)
    return client.get(following_url(target) if q is None else f"{following_url(target)}?q={q}")


# --- Spec scenario: Following list shows followed users ----------------------


def test_following_list_shows_followed_users(client):
    """Spec scenario: Following list shows followed users — the modal of a
    profile lists the users that profile follows (and only them), newest
    relationship first."""
    profile_user = make_user()
    bob = make_user("bob", first_name="Bob", last_name="Smith")
    carol = make_user("carol")
    dave = make_user("dave")
    make_user("stranger")
    follow(profile_user, bob)
    follow(profile_user, carol)
    follow(profile_user, dave)
    follow(carol, profile_user)  # carol follows back: never in the list

    response = get_following(client, profile_user, profile_user)

    assert response.status_code == 200
    content = response.content.decode()
    # The followed users appear, newest relationship first.
    assert "@bob" in content
    assert "Bob Smith" in content
    assert "@carol" in content
    assert "@dave" in content
    assert content.index("@dave") < content.index("@carol") < content.index("@bob")
    # Users the profile does not follow never appear.
    assert "@stranger" not in content
    assert "Not following anyone yet" not in content


def test_following_list_requires_login(client):
    """An anonymous visitor is redirected to the login page instead of
    seeing any following list (design decision 7: protected pages require
    login)."""
    target = make_user()

    response = client.get(following_url(target))

    assert response.status_code == 302
    assert "/web/login/" in response.url


def test_following_list_unknown_user_responds_404(client):
    """A well-formed but non-existent identifier answers 404, like the
    profile page (design decision 8)."""
    viewer = make_user()

    client.force_login(viewer)
    response = client.get(f"/web/profile/{uuid.uuid4()}/following/")

    assert response.status_code == 404


# --- Spec scenario: Following list search filters -----------------------------


def test_following_list_search_filters_by_username(client):
    """Spec scenario: Following list search filters — a query matching a
    username keeps only the followed user with that username."""
    profile_user = make_user()
    bob = make_user("bob")
    carol = make_user("carol")
    follow(profile_user, bob)
    follow(profile_user, carol)

    response = get_following(client, profile_user, profile_user, q="car")

    assert response.status_code == 200
    content = response.content.decode()
    assert "@carol" in content
    assert "@bob" not in content


def test_following_list_search_filters_by_name(client):
    """Spec scenario: Following list search filters — a query matching a
    first or last name (case-insensitive) keeps only the followed user with
    that name."""
    profile_user = make_user()
    bob = make_user("bob", first_name="Bob", last_name="Smith")
    carol = make_user("carol", first_name="Carol", last_name="Jones")
    follow(profile_user, bob)
    follow(profile_user, carol)

    by_first_name = get_following(client, profile_user, profile_user, q="jones")
    by_last_name = get_following(client, profile_user, profile_user, q="SMI")

    assert by_first_name.status_code == 200
    first_content = by_first_name.content.decode()
    assert "@carol" in first_content
    assert "@bob" not in first_content
    assert by_last_name.status_code == 200
    last_content = by_last_name.content.decode()
    assert "@bob" in last_content
    assert "@carol" not in last_content


def test_following_list_search_no_match_shows_empty_state(client):
    """A query that matches nobody renders the empty state instead of any
    user (the search filters, it never errors)."""
    profile_user = make_user()
    bob = make_user("bob")
    follow(profile_user, bob)

    response = get_following(client, profile_user, profile_user, q="zzz")

    assert response.status_code == 200
    content = response.content.decode()
    assert "@bob" not in content
    assert 'No results for "zzz"' in content


def test_following_list_search_matches_only_profile_own_follows(client):
    """The search filters the profile's own follows only: a query matching a
    user the profile does NOT follow yields the empty state, not that user."""
    profile_user = make_user()
    visitor = make_user("visitor")
    carol = make_user("carol")
    follow(visitor, carol)  # the viewer follows carol; the profile does not

    response = get_following(client, visitor, profile_user, q="carol")

    assert response.status_code == 200
    content = response.content.decode()
    assert "@carol" not in content
    assert 'No results for "carol"' in content
