from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"


def _login(client, username: str = "alice", password: str = "password123") -> dict:
    client.post(
        REGISTER_URL,
        {"username": username, "email": "alice@example.com", "password": password},
        format="json",
    )
    response = client.post(LOGIN_URL, {"username": username, "password": password}, format="json")
    return response.json()


@pytest.mark.django_db
class TestRefreshAPI:
    def test_successful_token_refresh(self, client) -> None:
        tokens = _login(client)

        response = client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["access"]
        assert "refresh" not in data

    def test_invalid_refresh_token_rejected(self, client, mocker) -> None:
        tokens = _login(client)

        for payload in [
            {},
            {"refresh": ""},
            {"refresh": "not-a-jwt"},
            {"refresh": tokens["access"]},
        ]:
            response = client.post(REFRESH_URL, payload, format="json")

            assert response.status_code == 401
            assert "access" not in response.json()

        mocker.patch.object(RefreshToken, "lifetime", timedelta(seconds=-1))
        expired = _login(client)

        response = client.post(REFRESH_URL, {"refresh": expired["refresh"]}, format="json")

        assert response.status_code == 401
        assert "access" not in response.json()
