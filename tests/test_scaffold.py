"""Scaffold smoke tests: configuration pinned by tasks 1.1 and 1.2."""

import json

from django.conf import settings


def test_auth_user_model_is_accounts_user():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_accounts_and_web_apps_registered():
    assert "apps.accounts" in settings.INSTALLED_APPS
    assert "apps.web" in settings.INSTALLED_APPS


def test_web_session_auth_urls():
    assert settings.LOGIN_URL == "/web/login/"
    assert settings.LOGIN_REDIRECT_URL == "/web/feed/"
    assert settings.LOGOUT_REDIRECT_URL == "/web/login/"


def test_jwt_lifetimes():
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() == 30 * 60
    assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds() == 24 * 60 * 60


def test_drf_uses_spectacular_schema():
    assert settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"


def test_openapi_schema_renders(client):
    response = client.get("/schema/")
    assert response.status_code == 200


def test_swagger_ui_renders(client):
    response = client.get("/docs/")
    assert response.status_code == 200


def test_schema_includes_auth_operations(client):
    """Task 6.2: the OpenAPI document exposes the register/login/refresh operations."""
    response = client.get("/schema/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    paths = json.loads(response.content)["paths"]
    auth_paths = {"/api/auth/register/", "/api/auth/login/", "/api/auth/refresh/"}
    assert auth_paths <= paths.keys()
    for path in auth_paths:
        assert "post" in paths[path]
