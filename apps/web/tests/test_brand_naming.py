"""Brand naming: every user-visible product name is "Instagram".

Covers the "Brand naming" requirement of change
2026-11-08-08-style-auth-screens:
- Page titles carry the brand ("· Instagram" suffix, "Instagram" default).
- The auth wordmark shows the brand (CSS-generated, checked in style.css).
- The sidebar and sidebar footer show the brand.
"""

import re
from pathlib import Path

import pytest

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"

STYLE_CSS_PATH = Path(__file__).resolve().parents[1] / "static" / "web" / "style.css"
TEMPLATES_PATH = Path(__file__).resolve().parents[1] / "templates" / "web"

BASE_TEMPLATES = (TEMPLATES_PATH / "base.html", TEMPLATES_PATH / "base_auth.html")


def _title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    assert match, "page renders without a <title>"
    return match.group(1).strip()


def _register_and_login(client, username: str = "alice") -> None:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})


@pytest.mark.django_db
class TestPageTitlesCarryTheBrand:
    def test_page_titles_carry_the_brand(self, client) -> None:
        # Anonymous pages.
        assert _title(client.get(LOGIN_URL).content.decode()) == "Login · Instagram"
        assert _title(client.get(REGISTER_URL).content.decode()) == "Create account · Instagram"

        # Authenticated pages.
        _register_and_login(client)
        assert _title(client.get(FEED_URL).content.decode()) == "Feed · Instagram"

        from apps.accounts.models import User

        user = User.objects.get(username="alice")
        profile_html = client.get(f"/web/profile/{user.pk}/").content.decode()
        assert _title(profile_html) == "alice · Instagram"
        following_html = client.get(f"/web/profile/{user.pk}/following/").content.decode()
        assert _title(following_html) == "Following · alice · Instagram"

    def test_base_templates_default_to_the_brand_name(self) -> None:
        # Every shipped page overrides the title block, so the default title
        # only ever renders for future pages; both base layouts must default
        # to exactly "Instagram" (no legacy brand left behind).
        for path in BASE_TEMPLATES:
            html = path.read_text(encoding="utf-8")
            assert "{% block title %}Instagram{% endblock %}" in html
            assert "django_ig" not in html


@pytest.mark.django_db
class TestAuthWordmarkShowsTheBrand:
    def test_auth_wordmark_shows_the_brand(self, client) -> None:
        # The wordmark is CSS-generated (::after), so the DOM intentionally
        # carries no text: the honest check reads the generated content in
        # style.css (same mechanism as the brand-style test) and confirms the
        # auth logo partial renders no legacy wordmark.
        css = STYLE_CSS_PATH.read_text(encoding="utf-8")
        logo_rule = css.split(".auth-logo-brand::after", 1)[1].split("}", 1)[0]
        assert 'content: "Instagram"' in logo_rule

        for url in (LOGIN_URL, REGISTER_URL):
            html = client.get(url).content.decode()
            assert 'class="auth-logo auth-logo-brand"' in html
            assert "django_ig" not in re.sub(r"<title>.*?</title>", "", html)


@pytest.mark.django_db
class TestSidebarAndFooterShowTheBrand:
    def test_sidebar_and_footer_show_the_brand(self, client) -> None:
        _register_and_login(client)

        # The sidebar is part of base.html, so every authenticated page
        # renders it; the "© 2026 Instagram" footer lives only in the feed
        # sidebar partial.
        from apps.accounts.models import User

        user = User.objects.get(username="alice")
        authenticated_pages = (
            FEED_URL,
            f"/web/profile/{user.pk}/",
            f"/web/profile/{user.pk}/following/",
        )
        for url in authenticated_pages:
            html = client.get(url).content.decode()
            assert '<span class="sidebar-label">Instagram</span>' in html
            assert "django_ig" not in html

        feed_html = client.get(FEED_URL).content.decode()
        assert 'data-testid="sidebar-footer-copy">&copy; 2026 Instagram</p>' in feed_html

        # Pages other than the feed render the base sidebar without the
        # feed-only footer.
        for url in authenticated_pages[1:]:
            html = client.get(url).content.decode()
            assert 'data-testid="sidebar-footer-copy"' not in html
