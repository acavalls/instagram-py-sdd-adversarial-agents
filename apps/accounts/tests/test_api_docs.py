import json

from rest_framework.test import APIClient

SCHEMA_URL = "/schema/"
DOCS_URL = "/docs/"


class TestOpenAPIDocumentation:
    def test_schema_endpoint_serves_the_api_contract(self) -> None:
        client = APIClient()

        response = client.get(SCHEMA_URL, {"format": "json"})

        assert response.status_code == 200
        document = json.loads(response.content)
        assert document["openapi"].startswith("3.")
        paths = document["paths"]
        assert "post" in paths["/api/auth/register/"]
        assert "post" in paths["/api/auth/login/"]
        assert "post" in paths["/api/auth/refresh/"]
        register_request = paths["/api/auth/register/"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        assert register_request.endswith("/UserCreate")
        # The posts surface is part of the contract now (MODIFIED delta).
        assert "get" in paths["/api/posts/"]
        assert "post" in paths["/api/posts/"]
        posts_detail = paths["/api/posts/{post_id}/"]
        assert "get" in posts_detail
        assert "patch" in posts_detail
        assert "delete" in posts_detail
        posts_request = paths["/api/posts/"]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]["$ref"]
        assert posts_request.endswith("/PostWrite")

    def test_docs_ui_renders(self) -> None:
        client = APIClient()

        response = client.get(DOCS_URL)

        assert response.status_code == 200
        page = response.content.decode()
        assert "SwaggerUIBundle" in page
        assert "/schema/" in page
