"""api-docs scenario tests (task 9.2, delta spec: OpenAPI documentation).

The endpoints already exist in ``config/urls.py`` (drf-spectacular); these
tests pin the two spec scenarios: Schema endpoint serves the API contract,
Docs UI renders."""

import json


def test_schema_endpoint_serves_the_api_contract(client):
    """WHEN a client requests /schema/?format=json
    THEN the system responds 200 with an OpenAPI document including the
    authentication and posts paths."""
    response = client.get("/schema/?format=json")

    assert response.status_code == 200
    document = json.loads(response.content)
    assert document["openapi"].startswith("3.")
    paths = document["paths"]
    auth_paths = {"/api/auth/register/", "/api/auth/login/", "/api/auth/refresh/"}
    posts_paths = {"/api/posts/", "/api/posts/{id}/"}
    assert auth_paths <= paths.keys()
    assert posts_paths <= paths.keys()
    for path in auth_paths | posts_paths:
        assert "get" in paths[path] or "post" in paths[path]


def test_docs_ui_renders(client):
    """WHEN a user opens /docs/
    THEN the system responds 200 with the Swagger UI page."""
    response = client.get("/docs/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "swagger-ui" in content
