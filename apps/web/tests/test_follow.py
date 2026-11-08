"""Web follow/unfollow via HTMX (social: "Follow and unfollow actions")."""

import json
import uuid

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"


def _register_and_login(client: Client, username: str) -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _follow_url(user: User) -> str:
    return f"/web/profile/{user.pk}/follow/"


def _unfollow_url(user: User) -> str:
    return f"/web/profile/{user.pk}/unfollow/"


def _toast(response) -> str:
    return json.loads(response["HX-Trigger"])["toast"]


@pytest.mark.django_db
class TestWebFollowViaHtmx:
    def test_web_follow_via_htmx(self, client: Client) -> None:
        bob = _register_and_login(client, "bob")
        alice = _register_and_login(client, "alice")

        response = client.post(_follow_url(bob), headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="follow-button"' in html
        assert 'data-following="true"' in html
        assert "Following" in html
        assert _toast(response) == "Followed successfully"
        assert FollowService().is_following(alice, bob)

    def test_web_unfollow_via_htmx(self, client: Client) -> None:
        bob = _register_and_login(client, "bob")
        alice = _register_and_login(client, "alice")
        FollowService().follow(follower=alice, following=bob)

        response = client.post(_unfollow_url(bob), headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="follow-button"' in html
        assert 'data-following="false"' in html
        assert "Follow" in html
        assert _toast(response) == "Unfollowed successfully"
        assert not FollowService().is_following(alice, bob)


@pytest.mark.django_db
class TestWebFollowFailureShowsTheCause:
    def test_duplicate_follow_keeps_state_with_error_toast(self, client: Client) -> None:
        bob = _register_and_login(client, "bob")
        alice = _register_and_login(client, "alice")
        FollowService().follow(follower=alice, following=bob)

        response = client.post(_follow_url(bob), headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-following="true"' in html
        assert "Following" in html
        assert _toast(response) == "Already following this user"
        assert FollowService().is_following(alice, bob)

    def test_self_follow_keeps_state_with_error_toast(self, client: Client) -> None:
        alice = _register_and_login(client, "alice")

        response = client.post(_follow_url(alice), headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-following="false"' in html
        assert "Follow" in html
        assert _toast(response) == "You cannot follow yourself"
        assert not FollowService().is_following(alice, alice)

    def test_unfollow_unknown_relationship_keeps_state_with_error_toast(
        self, client: Client
    ) -> None:
        bob = _register_and_login(client, "bob")
        alice = _register_and_login(client, "alice")

        response = client.post(_unfollow_url(bob), headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="follow-button"' in html
        assert 'data-following="false"' in html
        assert "Follow" in html
        assert _toast(response) == "Follow relationship not found"
        assert not FollowService().is_following(alice, bob)


@pytest.mark.django_db
class TestWebFollowAccessControl:
    def test_web_follow_requires_login(self, client: Client) -> None:
        bob = _register_and_login(client, "bob")
        client.logout()

        response = client.post(_follow_url(bob))

        assert response.status_code == 302
        assert LOGIN_URL in response["Location"]

    def test_web_follow_unknown_target_responds_404(self, client: Client) -> None:
        _register_and_login(client, "alice")

        response = client.post(f"/web/profile/{uuid.uuid4()}/follow/")

        assert response.status_code == 404
