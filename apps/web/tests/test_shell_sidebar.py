import re

import pytest

from apps.accounts.models import User

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"
PLACEHOLDER_ENTRIES = ("Search", "Explore", "Messages", "Notifications")


def _register_and_login(client, username: str = "alice") -> None:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})


def _profile_url(user: User) -> str:
    return f"/web/profile/{user.pk}/"


def _feed_html(client) -> str:
    return client.get(FEED_URL).content.decode()


def _tag(html: str, testid: str) -> str:
    match = re.search(rf"<a [^>]*data-testid=\"{testid}\"[^>]*>", html)
    assert match, f"anchor {testid} not found"
    return match.group(0)


@pytest.mark.django_db
class TestSidebarShell:
    def test_sidebar_renders_navigation_for_authenticated_user(self, client) -> None:
        _register_and_login(client)

        html = _feed_html(client)

        assert 'data-testid="sidebar"' in html
        assert 'data-testid="sidebar-logo"' in html
        assert 'data-testid="logout-form"' in html
        nav_entries = (
            "Home",
            "Search",
            "Explore",
            "Messages",
            "Notifications",
            "Create",
            "Profile",
        )
        for entry in nav_entries:
            assert f">{entry}</span>" in html

    def test_placeholder_entries_have_no_destination(self, client) -> None:
        _register_and_login(client)

        html = _feed_html(client)
        tags = re.findall(r"<a [^>]*sidebar-link--placeholder[^>]*>", html)

        assert len(tags) == len(PLACEHOLDER_ENTRIES)
        for tag in tags:
            assert "href" not in tag
            assert 'aria-disabled="true"' in tag

    def test_logo_links_to_the_home_feed(self, client) -> None:
        _register_and_login(client)

        html = _feed_html(client)

        assert 'href="/web/feed/"' in _tag(html, "sidebar-logo")

    def test_logout_available_at_the_sidebar_bottom(self, client) -> None:
        _register_and_login(client)

        html = _feed_html(client)

        assert 'data-testid="logout-form"' in html
        assert 'method="post"' in html
        assert 'action="/web/logout/"' in html
        assert "csrfmiddlewaretoken" in html
        assert html.index('data-testid="logout-form"') > html.index('data-testid="nav-profile"')

    def test_anonymous_pages_render_without_sidebar(self, client) -> None:
        login_html = client.get(LOGIN_URL).content.decode()
        register_html = client.get(REGISTER_URL).content.decode()

        assert 'data-testid="sidebar"' not in login_html
        assert 'data-testid="sidebar"' not in register_html

    def test_active_link_reflects_current_page(self, client) -> None:
        _register_and_login(client)

        html = _feed_html(client)

        assert " active" in _tag(html, "nav-home")
        for testid in (
            "nav-search",
            "nav-explore",
            "nav-messages",
            "nav-notifications",
            "nav-profile",
        ):
            assert "active" not in _tag(html, testid)
        create_form = re.search(r"<form [^>]*data-testid=\"nav-create\"[^>]*>", html)
        assert create_form, "create form not found"
        assert "active" not in create_form.group(0)

    def test_active_navigation_holds_on_profile_pages(self, client) -> None:
        _register_and_login(client)
        user = User.objects.get(username="alice")

        profile_html = client.get(_profile_url(user)).content.decode()
        assert " active" in _tag(profile_html, "nav-profile")
        assert "active" not in _tag(profile_html, "nav-home")

        following_html = client.get(f"{_profile_url(user)}following/").content.decode()
        assert " active" in _tag(following_html, "nav-profile")
        assert "active" not in _tag(following_html, "nav-home")

    def test_icon_font_is_loaded(self, client) -> None:
        _register_and_login(client)

        assert "bootstrap-icons" in _feed_html(client)
        assert "bootstrap-icons" in client.get(LOGIN_URL, follow=True).content.decode()
