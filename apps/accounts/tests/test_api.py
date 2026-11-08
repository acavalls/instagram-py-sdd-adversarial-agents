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

    def test_api_registration_does_not_require_authentication(self) -> None:
        client = APIClient()

        response = client.post(
            REGISTER_URL,
            {"username": "anon1", "email": "anon@example.com", "password": "password123"},
            format="json",
        )

        assert response.status_code == 201
