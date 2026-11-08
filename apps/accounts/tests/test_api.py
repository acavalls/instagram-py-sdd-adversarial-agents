import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

REGISTER_URL = "/api/auth/register/"


@pytest.mark.django_db
class TestRegisterAPI:
    def test_successful_api_registration(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        assert data["bio"] == ""
        assert data["id"]
        assert data["updated_at"]
        assert User.objects.filter(username="alice").exists()

    def test_api_registration_conflict_email(self) -> None:
        client = APIClient()
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        response = client.post(
            REGISTER_URL,
            {"username": "bob", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 409
        assert response.json() == {"error": "Email already registered"}

    def test_api_registration_conflict_username(self) -> None:
        client = APIClient()
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        response = client.post(
            REGISTER_URL,
            {"username": "alice", "email": "bob@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 409
        assert response.json() == {"error": "Username already taken"}

    def test_api_registration_validation_error_password_too_short(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "short"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["password"] == ["Password must be at least 8 characters"]
        assert not User.objects.exists()

    def test_api_registration_validation_error_username_format(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "ab!", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["username"] == ["Username must contain only letters and numbers"]

    def test_api_registration_validation_error_bad_email(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "alice", "email": "not-an-email", "password": "password123"},
            format="json",
        )

        assert response.status_code == 400
        assert "email" in response.json()

    def test_api_registration_trims_the_email_whitespace(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "alice", "email": "  padded@example.com  ", "password": "password123"},
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "padded@example.com"
        assert User.objects.get(username="alice").email == "padded@example.com"

        # Uniqueness is enforced on the trimmed value.
        duplicate = client.post(
            REGISTER_URL,
            {"username": "bob", "email": "padded@example.com", "password": "password123"},
            format="json",
        )

        assert duplicate.status_code == 409
        assert duplicate.json() == {"error": "Email already registered"}

    def test_api_endpoints_accept_session_cookie_authentication(self) -> None:
        client = APIClient()
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )

        session_client = APIClient()
        session_client.force_login(User.objects.get(username="alice"))

        response = session_client.get("/api/posts/")

        assert response.status_code == 200
        assert response.json() == []

        anonymous = APIClient()

        anonymous_response = anonymous.get("/api/posts/")

        # 403, not 401: SessionAuthentication (first in the defaults) does not
        # issue a WWW-Authenticate challenge for anonymous requests.
        assert anonymous_response.status_code == 403

    def test_api_registration_does_not_require_authentication(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "anon1", "email": "anon@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 201


@pytest.mark.django_db
class TestAPISessionAuthSemantics:
    def test_session_identity_wins_over_a_presented_jwt(self) -> None:
        client = APIClient()
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )
        session_client = APIClient()
        session_client.force_login(User.objects.get(username="alice"))

        other = APIClient()
        other.post(
            REGISTER_URL,
            {"username": "bob", "email": "bob@example.com", "password": "password123"},
            format="json",
        )
        bob_tokens = other.post(
            "/api/auth/login/",
            {"username": "bob", "password": "password123"},
            format="json",
        ).json()

        response = session_client.post(
            "/api/posts/",
            {"caption": "whose post?"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {bob_tokens['access']}",
        )

        assert response.status_code == 201
        assert response.json()["owner_username"] == "alice"

    def test_csrf_is_enforced_on_session_authenticated_unsafe_methods(self) -> None:
        client = APIClient(enforce_csrf_checks=True)
        client.post(
            REGISTER_URL,
            {"username": "alice", "email": "alice@example.com", "password": "password123"},
            format="json",
        )
        client.force_login(User.objects.get(username="alice"))

        response = client.post("/api/posts/", {"caption": "no csrf"}, format="json")

        assert response.status_code == 403

    def test_anonymous_requests_are_rejected_without_a_challenge(self) -> None:
        client = APIClient()

        response = client.get("/api/posts/")

        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers
