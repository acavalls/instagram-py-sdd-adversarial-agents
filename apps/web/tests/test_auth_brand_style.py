from pathlib import Path

import pytest

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"

STYLE_CSS_PATH = Path(__file__).resolve().parents[1] / "static" / "web" / "style.css"

GRADIENT_COLORS = ("#833ab4", "#fd1d1d", "#fcb045")


def _auth_page_rule(css: str) -> str:
    return css.split(".auth-page", 1)[1].split("}", 1)[0]


@pytest.mark.django_db
class TestAuthScreensUseTheBrandVisualStyle:
    def test_auth_screens_use_the_brand_visual_style(self, client) -> None:
        for url in (LOGIN_URL, REGISTER_URL):
            response = client.get(url)

            assert response.status_code == 200
            html = response.content.decode()
            assert "fonts.googleapis.com" in html
            assert "family=Grand+Hotel" in html
            assert "family=Inter" in html
            assert "display=swap" in html
            assert "/static/web/style.css" in html

        css = STYLE_CSS_PATH.read_text(encoding="utf-8")
        auth_page_rule = _auth_page_rule(css)
        assert "linear-gradient" in auth_page_rule
        for color in GRADIENT_COLORS:
            assert color in auth_page_rule
