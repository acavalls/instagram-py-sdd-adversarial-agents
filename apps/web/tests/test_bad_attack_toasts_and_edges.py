"""Bad attack (GBU): toast rendering, CSRF on logout, email case variants."""

import pytest
from django.test import Client

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _register(client: Client, username: str, email: str, password: str):
    return client.post(
        "/web/register/",
        {"username": username, "email": email, "password": password},
    )


class TestToastRendering:
    def test_login_success_toast_is_rendered_on_feed_page(self):
        User.objects.create(username="toastuser", email="toast@x.com", password="password123")
        client = Client()
        response = client.post(
            "/web/login/", {"username": "toastuser", "password": "password123"}, follow=True
        )
        assert response.status_code == 200
        assert "Logged in successfully" in response.content.decode()

    def test_logout_toast_is_rendered_on_login_page(self):
        User.objects.create(username="outuser", email="out@x.com", password="password123")
        client = Client()
        client.force_login(User.objects.get(username="outuser"))
        response = client.post("/web/logout/", follow=True)
        assert "You have been logged out" in response.content.decode()

    def test_register_toast_is_rendered_on_login_page(self):
        client = Client()
        _register(client, "regtoast", "regtoast@x.com", "password123")
        response = client.get("/web/login/")
        assert "Account created successfully. Please login." in response.content.decode()


class TestLogoutCsrf:
    def test_logout_post_without_csrf_token_is_rejected(self):
        User.objects.create(username="csrfuser", email="csrf@x.com", password="password123")
        client = Client(enforce_csrf_checks=True)
        client.force_login(User.objects.get(username="csrfuser"))
        response = client.post("/web/logout/")
        assert response.status_code == 403


class TestEmailCaseVariants:
    def test_uppercased_email_variant_is_accepted_byte_exact_uniqueness(self):
        User.objects.create(username="caseone", email="foo@x.com", password="password123")
        client = Client()
        response = _register(client, "casetwo", "FOO@x.com", "password123")
        assert response.status_code == 302
        assert User.objects.get(username="casetwo").email == "FOO@x.com"

    def test_domain_case_email_variant_is_accepted_byte_exact_uniqueness(self):
        User.objects.create(username="caseone", email="foo@x.com", password="password123")
        client = Client()
        response = _register(client, "casetwo", "foo@X.COM", "password123")
        assert response.status_code == 302
        assert User.objects.get(username="casetwo").email == "foo@X.COM"
        assert User.objects.filter(email="foo@X.COM").count() == 1
        assert User.objects.filter(email="foo@x.com").count() == 1

    def test_identical_email_is_rejected_as_duplicate(self):
        User.objects.create(username="caseone", email="foo@x.com", password="password123")
        client = Client()
        response = _register(client, "casetwo", "foo@x.com", "password123")
        assert response.status_code == 200
        assert "Email already registered" in response.content.decode()
        assert User.objects.filter(email="foo@x.com").count() == 1
