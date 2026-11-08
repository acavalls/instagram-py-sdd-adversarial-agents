"""Home feed suggestions panel and sidebar chrome (social: "User suggestions")."""

import re
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"


def _register_and_login(client: Client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _login(client: Client, username: str) -> User:
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _set_date_joined(user: User, days_ago: int) -> None:
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))


def _suggestion_rows(html: str) -> list[str]:
    """The usernames of the rendered suggestion rows, in render order."""
    return re.findall(
        r'data-testid="suggestion-row".*?data-testid="suggestion-username">(\w+)</a>',
        html,
        flags=re.DOTALL,
    )


def _follow_url(user: User) -> str:
    return f"/web/profile/{user.pk}/follow/"


def _unfollow_url(user: User) -> str:
    return f"/web/profile/{user.pk}/unfollow/"


@pytest.mark.django_db
class TestSuggestionsExcludeFollowedUsersAndSelf:
    def test_suggestions_exclude_followed_users_and_self(self, client: Client) -> None:
        user = _register_and_login(client)
        followed = _register_and_login(client, "bob")
        stranger = _register_and_login(client, "carol")
        _set_date_joined(user, days_ago=10)
        _set_date_joined(followed, days_ago=5)
        _set_date_joined(stranger, days_ago=1)
        FollowService().follow(follower=user, following=followed)
        _login(client, "alice")

        html = client.get(FEED_URL).content.decode()

        rows = _suggestion_rows(html)
        assert rows == ["carol"]
        assert "alice" not in rows
        assert "bob" not in rows


@pytest.mark.django_db
class TestSuggestionsLimitedToNewestAccounts:
    def test_suggestions_limited_to_newest_accounts(self, client: Client) -> None:
        user = _register_and_login(client)
        candidates = [_register_and_login(client, f"user{index}") for index in range(1, 7)]
        for index, candidate in enumerate(candidates):
            _set_date_joined(candidate, days_ago=10 - index)
        _set_date_joined(user, days_ago=30)
        _login(client, "alice")

        html = client.get(FEED_URL).content.decode()

        rows = _suggestion_rows(html)
        assert len(rows) == 5
        newest_first = list(reversed(candidates))[:5]
        assert rows == [candidate.username for candidate in newest_first]


@pytest.mark.django_db
class TestSuggestionsRenderAsARightHandColumn:
    def test_suggestions_render_as_a_right_hand_column_with_follow_buttons(
        self, client: Client
    ) -> None:
        _register_and_login(client)
        suggested = _register_and_login(client, "bob")
        _login(client, "alice")

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="home-sidebar"' in html
        assert 'data-testid="suggestions"' in html
        assert 'data-testid="suggestion-row"' in html
        assert 'data-testid="suggestion-avatar"' in html
        assert f'data-testid="suggestion-username">{suggested.username}</a>' in html
        assert f'href="/web/profile/{suggested.pk}/"' in html
        assert 'data-testid="suggestion-reason"' in html
        assert 'data-testid="follow-button"' in html
        assert 'data-following="false"' in html
        assert f'hx-post="{_follow_url(suggested)}"' in html
        assert _suggestion_rows(html) == ["bob"]


@pytest.mark.django_db
class TestSuggestionFollowButtonTogglesTheRelationship:
    def test_suggestion_follow_button_reflects_and_toggles_the_relationship(
        self, client: Client
    ) -> None:
        user = _register_and_login(client)
        suggested = _register_and_login(client, "bob")
        _login(client, "alice")

        html = client.get(FEED_URL).content.decode()
        assert _suggestion_rows(html) == ["bob"]
        assert 'data-following="false"' in html

        follow_response = client.post(_follow_url(suggested), headers={"HX-Request": "true"})
        assert follow_response.status_code == 200
        follow_html = follow_response.content.decode()
        assert 'data-following="true"' in follow_html
        assert "Following" in follow_html
        assert FollowService().is_following(user, suggested)

        html = client.get(FEED_URL).content.decode()
        assert _suggestion_rows(html) == []

        unfollow_response = client.post(_unfollow_url(suggested), headers={"HX-Request": "true"})
        assert unfollow_response.status_code == 200
        unfollow_html = unfollow_response.content.decode()
        assert 'data-following="false"' in unfollow_html
        assert "Follow" in unfollow_html
        assert not FollowService().is_following(user, suggested)

        html = client.get(FEED_URL).content.decode()
        assert _suggestion_rows(html) == ["bob"]
        assert 'data-following="false"' in html


@pytest.mark.django_db
class TestSidebarCurrentUserBlockAndFooter:
    def test_sidebar_renders_the_current_user_block_and_footer(self, client: Client) -> None:
        user = _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="sidebar-current-user"' in html
        assert 'data-testid="current-user-avatar"' in html
        assert f'data-testid="current-user-username">{user.username}</a>' in html
        assert f'href="/web/profile/{user.pk}/"' in html
        assert 'data-testid="sidebar-footer"' in html
        for label in ("About", "Help", "API", "Jobs", "Privacy", "Terms"):
            assert f">{label}</a>" in html


@pytest.mark.django_db
class TestNoCandidatesShowsTheEmptyMessage:
    def test_no_candidates_shows_the_empty_message(self, client: Client) -> None:
        _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        assert 'data-testid="suggestions-empty"' in html
        assert "No suggestions right now." in html
        assert 'data-testid="suggestion-row"' not in html
