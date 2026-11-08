"""Bad attack (GBU cycle 9) against change 2026-11-08-09-final-drift-cleanup.

The change *declares* (no production code) three semantics:
  1. Session identity wins over any presented JWT — attacked here with an
     INVALID (malformed) JWT and an EXPIRED-but-validly-signed JWT beside a
     valid session, plus a consistent-identity (same user) pair.
  2. CSRF on session-authenticated unsafe methods — attacked on PATCH and
     DELETE (prior cycle only covered POST), plus the positive case (valid
     CSRF token is accepted) and CSRF-with-foreign-JWT.
  3. Anonymous requests → 403 with no WWW-Authenticate — attacked on
     endpoints other than the POST list (detail GET, detail PATCH), plus a
     probe of anonymous-with-garbage-JWT (documents the 401+challenge
     surface the declaration does not cover).

Regression sanity: JWT-only writes, brand titles, feed-only footer, and the
social "Topbar links to own profile" scenario on a NON-feed authenticated
page (the declared scenario says "any authenticated web page").
"""

import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

pytestmark = pytest.mark.django_db

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
POSTS = "/api/posts/"
FEED_URL = "/web/feed/"


def _register(client, username="alice", password="password123"):
    return client.post(
        REGISTER,
        {
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
        format="json",
    )


def _login(client, username, password="password123"):
    return client.post(LOGIN, {"username": username, "password": password}, format="json")


def _create_post(client, caption):
    return client.post(POSTS, {"caption": caption}, format="json")


class TestSessionWinsOverPresentedJWT:
    def _session_client(self, username="alice"):
        client = APIClient(enforce_csrf_checks=True)
        _register(client, username)
        from apps.accounts.models import User

        client.force_login(User.objects.get(username=username))
        # Obtain a CSRF cookie the way a browser session would (a page that
        # renders a form for the authenticated user).
        page = client.get(FEED_URL)
        assert page.status_code == 200
        client._csrf = client.cookies["csrftoken"].value
        return client

    def _csrf_post(self, client, payload, **extra):
        return client.post(
            POSTS,
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=client._csrf,
            **extra,
        )

    def test_malformed_jwt_alongside_valid_session_still_acts_as_session_user(self):
        client = self._session_client()

        response = self._csrf_post(
            client, {"caption": "session wins"},
            HTTP_AUTHORIZATION="Bearer not.a.valid.jwt",
        )

        assert response.status_code == 201, response.content
        assert response.json()["owner_username"] == "alice"

    def test_expired_validly_signed_jwt_alongside_valid_session_still_loses(self):
        client = self._session_client()
        from apps.accounts.models import User

        expired = AccessToken.for_user(User.objects.get(username="alice"))
        expired.set_exp(
            from_time=datetime.now(UTC) - timedelta(hours=2),
            lifetime=timedelta(seconds=1),
        )

        response = self._csrf_post(
            client, {"caption": "expired jwt loses"},
            HTTP_AUTHORIZATION=f"Bearer {expired}",
        )

        assert response.status_code == 201, response.content
        assert response.json()["owner_username"] == "alice"

    def test_consistent_identity_session_plus_own_jwt_is_accepted(self):
        client = self._session_client()
        tokens = _login(APIClient(), "alice").json()

        response = client.get(POSTS, HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        assert response.status_code == 200

    def test_csrf_still_enforced_when_foreign_jwt_is_also_presented(self):
        client = self._session_client()
        other = APIClient()
        _register(other, "bob")
        bob_tokens = _login(other, "bob").json()

        response = client.post(
            POSTS,
            {"caption": "csrf must still bite"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {bob_tokens['access']}",
        )

        assert response.status_code == 403


class TestCSRFOnSessionUnsafeMethods:
    def _session_client_with_post(self, enforce_csrf=True):
        client = APIClient(enforce_csrf_checks=enforce_csrf)
        _register(client)
        from apps.accounts.models import User

        client.force_login(User.objects.get(username="alice"))
        page = client.get(FEED_URL)
        assert page.status_code == 200
        csrf = client.cookies["csrftoken"].value

        created = client.post(
            POSTS, {"caption": "target post"}, format="json", HTTP_X_CSRFTOKEN=csrf
        )
        assert created.status_code == 201
        post_id = created.json()["id"]
        return client, post_id

    def test_session_patch_without_csrf_is_403(self):
        client, post_id = self._session_client_with_post()

        response = client.patch(
            f"{POSTS}{post_id}/", {"caption": "hijacked"}, format="json"
        )

        assert response.status_code == 403

    def test_session_delete_without_csrf_is_403(self):
        client, post_id = self._session_client_with_post()

        response = client.delete(f"{POSTS}{post_id}/")

        assert response.status_code == 403

    def test_session_post_with_valid_csrf_token_is_accepted(self):
        client, _ = self._session_client_with_post(enforce_csrf=False)

        # Obtain a real CSRF token cookie the way a browser would.
        page = client.get(FEED_URL)
        assert page.status_code == 200
        token = client.cookies["csrftoken"].value

        fresh = APIClient(enforce_csrf_checks=True)
        from apps.accounts.models import User

        fresh.force_login(User.objects.get(username="alice"))
        fresh.cookies["csrftoken"] = token

        response = fresh.post(
            POSTS,
            {"caption": "with csrf"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 201, response.content
        assert response.json()["owner_username"] == "alice"


class TestAnonymousNoChallengeSurface:
    def test_anonymous_detail_get_is_403_without_www_authenticate(self):
        client = APIClient()

        response = client.get(f"{POSTS}{uuid.uuid4()}/")

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers

    def test_anonymous_detail_patch_is_403_without_www_authenticate(self):
        client = APIClient()

        response = client.patch(
            f"{POSTS}{uuid.uuid4()}/", {"caption": "x"}, format="json"
        )

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers

    def test_anonymous_list_get_is_403_without_www_authenticate(self):
        client = APIClient()

        response = client.get(POSTS)

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers

    def test_anonymous_with_garbage_jwt_is_still_403_without_challenge(self):
        """Edge of the declared surface: an anonymous request presenting a
        MALFORMED bearer token makes JWTAuthentication raise Authentication
        Failed (401), but DRF downgrades it to 403 because the FIRST
        authenticator in DEFAULT_AUTHENTICATION_CLASSES (SessionAuthentica
        tion) defines no authenticate_header — so no WWW-Authenticate ever
        leaks. This pins the downgrade for the declared no-challenge rule."""
        client = APIClient()

        response = client.get(POSTS, HTTP_AUTHORIZATION="Bearer not.a.valid.jwt")

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers

    def test_anonymous_with_tampered_signature_jwt_is_403_without_challenge(self):
        _register(APIClient(), "alice")
        client = APIClient()
        tokens = _login(APIClient(), "alice").json()

        response = client.get(
            POSTS, HTTP_AUTHORIZATION=f"Bearer {tokens['access'][:-4]}AAAA"
        )

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers


class TestRegressionSanity:
    def test_jwt_only_write_still_works(self):
        client = APIClient()
        _register(client)
        tokens = _login(client, "alice").json()

        response = client.post(
            POSTS,
            {"caption": "jwt only"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )

        assert response.status_code == 201
        assert response.json()["owner_username"] == "alice"

    def test_brand_titles_and_feed_only_footer(self):
        from django.test import Client as DjangoClient
        from apps.accounts.models import User

        browser = DjangoClient()
        browser.post(
            "/web/register/",
            {
                "username": "branduser",
                "email": "branduser@example.com",
                "password": "password123",
            },
        )
        browser.post(
            "/web/login/", {"username": "branduser", "password": "password123"}
        )
        user = User.objects.get(username="branduser")

        feed = browser.get(FEED_URL)
        assert feed.status_code == 200
        assert "Feed · Instagram" in feed.content.decode()

        profile = browser.get(f"/web/profile/{user.pk}/")
        html = profile.content.decode()
        assert f"{user.username} · Instagram" in html
        # Footer must appear on the feed only.
        assert 'data-testid="sidebar-footer-copy"' not in html
        assert 'data-testid="sidebar-footer-copy"' in feed.content.decode()

    def test_nav_profile_link_present_on_non_feed_authenticated_page(self):
        """Social spec scenario 'Topbar links to own profile': WHEN a
        logged-in user views ANY authenticated web page THEN the sidebar
        shows a Profile link to their own profile. The twin tests only walk
        the feed; this attacks another authenticated page."""
        from django.test import Client as DjangoClient
        from apps.accounts.models import User

        browser = DjangoClient()
        browser.post(
            "/web/register/",
            {
                "username": "topbaruser",
                "email": "topbaruser@example.com",
                "password": "password123",
            },
        )
        browser.post(
            "/web/login/", {"username": "topbaruser", "password": "password123"}
        )
        user = User.objects.get(username="topbaruser")

        html = browser.get(f"/web/profile/{user.pk}/").content.decode()

        match = re.search(r'<a [^>]*data-testid="nav-profile"[^>]*>', html)
        assert match, "nav-profile anchor not found on profile page"
        assert f'href="/web/profile/{user.pk}/"' in match.group(0)
