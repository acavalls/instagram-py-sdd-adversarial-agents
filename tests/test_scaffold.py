from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase


def test_settings_bootstrap() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.LOGIN_URL == "/web/login/"
    assert settings.LOGIN_REDIRECT_URL == "/web/feed/"
    assert settings.LOGOUT_REDIRECT_URL == "/web/login/"


class ShellTemplatesTest(SimpleTestCase):
    def test_base_auth_renders_auth_shell(self) -> None:
        html = render_to_string("web/base_auth.html")
        assert 'class="auth-page"' in html
        assert "bootstrap-icons" in html

    def test_base_renders_shell_mount_points(self) -> None:
        html = render_to_string("web/base.html")
        assert 'id="messages"' in html
        assert 'id="modal-container"' in html
        assert "bootstrap-icons" in html
