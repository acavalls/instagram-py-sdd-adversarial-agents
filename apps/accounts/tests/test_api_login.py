import pytest

from apps.accounts.models import User
from apps.accounts.use_cases import ERROR_INVALID_CREDENTIALS

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"


def _register(client, username: str = "alice", email: str = "alice@example.com"):
    return client.post(
        REGISTER_URL,
        {"username": username, "email": email, "password": "password123"},
        format="json",
    )


def _login(client, username: str, password: str):
    return client.post(LOGIN_URL, {"username": username, "password": password}, format="json")


@pytest.mark.django_db
class TestLoginAPI:
    def test_successful_api_login(self, client) -> None:
        _register(client)

        response = _login(client, "alice", "password123")

        assert response.status_code == 200
        data = response.json()
        user = data["user"]
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["bio"] == ""
        assert user["id"]
        assert data["access"]
        assert data["refresh"]

    def test_api_login_trims_the_username_before_authentication(self, client) -> None:
        _register(client)

        response = _login(client, "  alice  ", "password123")

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "alice"
        assert data["access"]
        assert data["refresh"]

    def test_failed_api_login(self, client) -> None:
        _register(client)

        response = _login(client, "alice", "wrong-password")

        assert response.status_code == 401
        assert response.json() == {"error": ERROR_INVALID_CREDENTIALS}

    def test_api_login_with_missing_fields(self, client) -> None:
        _register(client)

        for payload in [
            {"username": "", "password": "password123"},
            {"username": "alice", "password": ""},
            {"username": "alice"},
            {"password": "password123"},
            {},
        ]:
            response = client.post(LOGIN_URL, payload, format="json")

            assert response.status_code == 401
            assert response.json() == {"error": ERROR_INVALID_CREDENTIALS}
            assert User.objects.count() == 1
