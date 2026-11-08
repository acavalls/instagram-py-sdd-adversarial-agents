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

    def test_docs_ui_renders(self) -> None:
        client = APIClient()

        response = client.get(DOCS_URL)

        assert response.status_code == 200
        page = response.content.decode()
        assert "SwaggerUIBundle" in page
        assert "/schema/" in page
