import uuid

import pytest

from apps.accounts.models import User
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"


def _register_and_login(client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _register_user(username: str, *, first_name: str = "", last_name: str = "") -> User:
    return User.objects.create(
        username=username,
        email=f"{username}@example.com",
        password="password123",
        first_name=first_name,
        last_name=last_name,
    )


def _following_url(user: User) -> str:
    return f"/web/profile/{user.pk}/following/"


@pytest.mark.django_db
class TestFollowingModal:
    def test_following_list_shows_followed_users(self, client) -> None:
        _register_and_login(client)
        owner = _register_user("owner")
        followed_one = _register_user("carol")
        followed_two = _register_user("dave")
        _register_user("erin")
        FollowService().follow(follower=owner, following=followed_one)
        FollowService().follow(follower=owner, following=followed_two)

        response = client.get(_following_url(owner))

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="following-modal"' in html
        assert 'data-testid="following-row"' in html
        assert 'data-testid="following-username"' in html
        assert "carol" in html
        assert "dave" in html
        assert "erin" not in html

    def test_following_list_search_filters(self, client) -> None:
        _register_and_login(client)
        owner = _register_user("owner")
        by_username = _register_user("matchuser")
        by_first_name = _register_user("unrelated1", first_name="Matcha", last_name="One")
        by_last_name = _register_user("unrelated2", first_name="Other", last_name="Matcher")
        _register_user("unrelated3", first_name="Zoe", last_name="Quiet")
        for followed in (by_username, by_first_name, by_last_name):
            FollowService().follow(follower=owner, following=followed)

        response = client.get(f"{_following_url(owner)}?q=match")

        assert response.status_code == 200
        html = response.content.decode()
        assert "matchuser" in html
        assert "unrelated1" in html
        assert "unrelated2" in html
        assert "unrelated3" not in html

    def test_following_list_search_htmx_returns_modal_partial(self, client) -> None:
        _register_and_login(client)
        owner = _register_user("owner")
        followed = _register_user("carol")
        other = _register_user("dave")
        FollowService().follow(follower=owner, following=followed)
        FollowService().follow(follower=owner, following=other)

        response = client.get(f"{_following_url(owner)}?q=carol", headers={"HX-Request": "true"})

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="following-modal"' in html
        assert 'data-testid="following-search-input"' in html
        assert 'value="carol"' in html
        assert "carol" in html
        assert "dave" not in html
        assert "<aside" not in html

    def test_following_modal_requires_login(self, client) -> None:
        owner = _register_user("owner")

        response = client.get(_following_url(owner))

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)

    def test_unknown_profile_following_list_responds_404(self, client) -> None:
        _register_and_login(client)

        response = client.get(f"/web/profile/{uuid.uuid4()}/following/")

        assert response.status_code == 404
