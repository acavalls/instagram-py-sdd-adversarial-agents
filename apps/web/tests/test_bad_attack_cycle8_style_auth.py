"""The Bad — cycle 8 adversarial attacks against 2026-11-08-08-style-auth-screens.

Attack targets:
1. Regression hunt: the restyle must not leak into any authenticated page.
2. Auth flows end-to-end through the restyled templates.
3. CSS-generated logo: no DOM double-render, pinned testids intact.
4. Fonts link present exactly once per auth page, absent elsewhere.
"""

import re

import pytest
from django.contrib.auth.hashers import make_password

from apps.accounts.models import User

LOGIN_URL = "/web/login/"
LOGOUT_URL = "/web/logout/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"
FONTS_LINK = "fonts.googleapis.com"


def _make_user(username: str) -> User:
    return User.objects.create(
        username=username,
        email=f"{username}@example.com",
        password=make_password("Str0ngPass!x"),
    )


@pytest.mark.django_db
class TestNoLeakIntoAuthenticatedPages:
    def test_feed_and_profile_do_not_load_auth_brand_style(self, client) -> None:
        _make_user("leakcheck")
        client.force_login(User.objects.get(username="leakcheck"))

        feed = client.get(FEED_URL)
        assert feed.status_code == 200
        feed_html = feed.content.decode()
        assert FONTS_LINK not in feed_html
        assert 'class="auth-page"' not in feed_html
        assert "auth-card" not in feed_html
        assert "auth-logo-brand" not in feed_html
        assert "auth-wrapper" not in feed_html
        assert 'data-testid="feed"' in feed_html
        assert 'data-testid="home-layout"' in feed_html
        assert 'data-testid="stories-bar"' in feed_html

        profile_user = _make_user("leakchecktarget")
        profile = client.get(f"/web/profile/{profile_user.pk}/")
        assert profile.status_code == 200
        profile_html = profile.content.decode()
        assert FONTS_LINK not in profile_html
        assert 'class="auth-page"' not in profile_html
        assert "auth-card" not in profile_html
        assert 'data-testid="profile"' in profile_html
        assert 'data-testid="profile-header"' in profile_html
        # The grid is present with posts; the empty state otherwise.
        assert (
            'data-testid="profile-grid"' in profile_html
            or 'data-testid="profile-empty"' in profile_html
        )

    def test_every_changed_css_selector_is_auth_scoped(self) -> None:
        # Static guard: no auth-* selector may match a non-auth template.
        changed_classes = ("auth-page", "auth-card", "auth-wrapper", "auth-logo-brand")
        template_dir = "apps/web/templates/web"
        import pathlib

        for path in pathlib.Path(template_dir).rglob("*.html"):
            html = path.read_text(encoding="utf-8")
            if path.name in {"base_auth.html", "login.html", "register.html"} or (
                path.parent.name == "partials" and path.name == "auth_logo.html"
            ):
                continue
            for cls in changed_classes:
                assert cls not in html, f"{path} unexpectedly uses {cls}"


@pytest.mark.django_db
class TestAuthFlowsOnRestyledTemplates:
    def test_wrong_login_rerenders_restyled_login_with_error(self, client) -> None:
        response = client.post(LOGIN_URL, {"username": "ghost", "password": "wrong"})
        assert response.status_code == 200
        html = response.content.decode()
        assert "Invalid credentials" in html
        # The error re-render must still be the restyled layout.
        assert FONTS_LINK in html
        assert 'class="auth-page"' in html

    def test_login_logout_and_register_roundtrip(self, client) -> None:
        signup = client.post(
            REGISTER_URL,
            {
                "username": "roundtrip",
                "email": "roundtrip@example.com",
                "password": "Str0ngPass!x",
            },
        )
        assert signup.status_code == 302
        login = client.post(LOGIN_URL, {"username": "roundtrip", "password": "Str0ngPass!x"})
        assert login.status_code == 302
        assert login.headers["Location"] == FEED_URL

        feed = client.get(FEED_URL)
        assert feed.status_code == 200
        assert "Logged in successfully" in feed.content.decode()

        logout = client.post(LOGOUT_URL)
        assert logout.status_code == 302
        assert logout.headers["Location"] == LOGIN_URL

        after_logout = client.get(LOGIN_URL)
        assert "You have been logged out" in after_logout.content.decode()

        register = client.post(
            REGISTER_URL,
            {
                "username": "freshuser",
                "email": "freshuser@example.com",
                "password": "Str0ngPass!x",
            },
        )
        assert register.status_code == 302
        assert register.headers["Location"] == LOGIN_URL
        created = User.objects.filter(username="freshuser").exists()
        assert created

        # The freshly registered user can log in through the restyled page.
        relogin = client.post(LOGIN_URL, {"username": "freshuser", "password": "Str0ngPass!x"})
        assert relogin.status_code == 302
        assert relogin.headers["Location"] == FEED_URL


@pytest.mark.django_db
class TestFontsLinkAndGeneratedLogo:
    def test_fonts_link_exactly_once_on_auth_pages_never_elsewhere(self, client) -> None:
        for url in (LOGIN_URL, REGISTER_URL):
            html = client.get(url).content.decode()
            assert html.count(FONTS_LINK) == 1, f"{url} loads Google Fonts != once"
            assert html.count("family=Grand+Hotel") == 1
            assert html.count("family=Inter") == 1

    def test_css_generated_logo_has_no_dom_wordmark_double_render(self, client) -> None:
        html = client.get(LOGIN_URL).content.decode()
        logo_match = re.search(
            r'<div class="auth-logo auth-logo-brand"[^>]*>.*?</div>', html, re.DOTALL
        )
        assert logo_match is not None
        logo_html = logo_match.group(0)
        # The wordmark lives only in the CSS ::after; the DOM must keep the
        # single pinned icon with no duplicated text content.
        assert logo_html.count('data-testid="auth-logo"') == 1
        assert logo_html.count("bi bi-instagram") == 1
        assert "django_ig" not in logo_html

    def test_anonymous_auth_pages_keep_pinned_testids(self, client) -> None:
        for url in (LOGIN_URL, REGISTER_URL):
            html = client.get(url).content.decode()
            assert 'data-testid="auth-logo"' in html
            assert "bi bi-instagram" in html
            assert 'class="auth-page"' in html
            assert "django_ig" not in re.sub(r"<title>.*?</title>", "", html)
