"""Bad attack (GBU): malformed API payloads and JWT cross-use."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


class TestApiMalformedPayloads:
    def _register(self, payload):
        client = APIClient()
        return client.post("/api/auth/register/", payload, format="json")

    def test_non_string_json_username_is_refused_or_valid(self):
        response = self._register(
            {"username": 1234567, "email": "int@x.com", "password": "password123"}
        )
        assert response.status_code in (201, 400)
        if response.status_code == 201:
            assert User.objects.filter(username="1234567").exists()

    def test_null_username_is_refused(self):
        response = self._register(
            {"username": None, "email": "null@x.com", "password": "password123"}
        )
        assert response.status_code == 400

    def test_null_password_is_refused(self):
        response = self._register(
            {"username": "nullpass", "email": "nullp@x.com", "password": None}
        )
        assert response.status_code == 400

    def test_boolean_password_is_refused(self):
        response = self._register({"username": "boolpass", "email": "bool@x.com", "password": True})
        assert response.status_code == 400

    def test_password_is_stored_and_compared_byte_exactly(self):
        response = self._register(
            {"username": "spaceuser", "email": "space@x.com", "password": " pass word "}
        )
        assert response.status_code == 201
        user = User.objects.get(username="spaceuser")
        assert user.check_password(" pass word ")
        assert not user.check_password("pass word")
        client = APIClient()
        login = client.post(
            "/api/auth/login/", {"username": "spaceuser", "password": " pass word "}, format="json"
        )
        assert login.status_code == 200

    def test_extra_unexpected_fields_are_ignored(self):
        response = self._register(
            {
                "username": "extrauser",
                "email": "extra@x.com",
                "password": "password123",
                "is_staff": True,
                "bio": "injected bio",
            }
        )
        assert response.status_code == 201
        user = User.objects.get(username="extrauser")
        assert not user.is_staff
        assert user.bio == ""

    def test_api_login_with_non_string_username_is_401(self):
        User.objects.create(username="apilogin", email="apilogin@x.com", password="password123")
        client = APIClient()
        response = client.post(
            "/api/auth/login/", {"username": 12345, "password": "password123"}, format="json"
        )
        assert response.status_code == 401


class TestJwtCrossUse:
    def test_access_token_cannot_be_used_as_refresh(self):
        user = User(username="jwtuser", email="jwt@x.com")
        user.set_password("password123")
        user.save()
        client = APIClient()
        login = client.post(
            "/api/auth/login/", {"username": "jwtuser", "password": "password123"}, format="json"
        )
        access = login.data["access"]
        response = client.post("/api/auth/refresh/", {"refresh": access}, format="json")
        assert response.status_code == 401
        assert "access" not in response.data

    def test_refresh_token_is_not_accepted_by_protected_flow_without_login(self):
        user = User(username="jwtuser2", email="jwt2@x.com")
        user.set_password("password123")
        user.save()
        client = APIClient()
        login = client.post(
            "/api/auth/login/", {"username": "jwtuser2", "password": "password123"}, format="json"
        )
        refresh = login.data["refresh"]
        bad = client.post("/api/auth/refresh/", {"refresh": refresh[:-2]}, format="json")
        assert bad.status_code == 401
