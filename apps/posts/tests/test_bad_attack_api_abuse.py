"""The Bad — attack tests for the posts REST API."""

import pytest
from rest_framework.test import APIClient

from apps.posts.models import CAPTION_MAX_LENGTH, Post

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
POSTS_URL = "/api/posts/"


def _auth_client(username: str = "alice") -> APIClient:
    client = APIClient()
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
        format="json",
    )
    response = client.post(
        LOGIN_URL, {"username": username, "password": "password123"}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return client


def _create_post(client: APIClient, caption: str = "hello") -> str:
    response = client.post(POSTS_URL, {"caption": caption}, format="multipart")
    assert response.status_code == 201, response.content
    return response.json()["id"]


@pytest.mark.django_db
class TestCrossUserVisibility:
    def test_detail_get_only_returns_the_authenticated_users_own_posts(self) -> None:
        """The visibility requirement: API endpoints MUST only return the
        authenticated user's own posts."""
        alice = _auth_client("alice")
        post_id = _create_post(alice, "alice only")
        bob = _auth_client("bob")

        response = bob.get(f"/api/posts/{post_id}/")

        assert response.status_code == 404, response.content
        assert response.json() == {"error": "Post not found"}


@pytest.mark.django_db
class TestPaginationAbuse:
    @pytest.mark.parametrize(
        "query", ["limit=0", "limit=-3", "offset=-1", "limit=abc", "offset=xyz"]
    )
    def test_invalid_pagination_values_are_rejected(self, query: str) -> None:
        alice = _auth_client("alice")
        response = alice.get(f"{POSTS_URL}?{query}")
        assert response.status_code == 400

    def test_huge_offset_returns_an_empty_window(self) -> None:
        alice = _auth_client("alice")
        _create_post(alice)
        response = alice.get(f"{POSTS_URL}?offset=999999&limit=5")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.django_db
class TestCaptionBoundaryPatch:
    def test_patch_caption_exactly_2200_applies_and_2201_is_refused(self) -> None:
        alice = _auth_client("alice")
        post_id = _create_post(alice, "hello")
        url = f"{POSTS_URL}{post_id}/"

        ok = alice.patch(url, {"caption": "x" * CAPTION_MAX_LENGTH}, format="json")
        assert ok.status_code == 200
        assert ok.json()["caption"] == "x" * CAPTION_MAX_LENGTH

        refused = alice.patch(url, {"caption": "x" * (CAPTION_MAX_LENGTH + 1)}, format="json")
        assert refused.status_code == 400
        assert Post.objects.get(pk=post_id).caption == "x" * CAPTION_MAX_LENGTH


@pytest.mark.django_db
class TestDeleteIdempotency:
    def test_second_delete_of_the_same_post_is_404(self) -> None:
        alice = _auth_client("alice")
        post_id = _create_post(alice)
        url = f"{POSTS_URL}{post_id}/"

        first = alice.delete(url)
        assert first.status_code == 204

        second = alice.delete(url)
        assert second.status_code == 404
        assert second.json() == {"error": "Post not found"}


@pytest.mark.django_db
class TestMalformedRequests:
    def test_create_with_no_fields_creates_an_empty_caption_post(self) -> None:
        alice = _auth_client("alice")
        response = alice.post(POSTS_URL, {}, format="multipart")
        assert response.status_code == 201
        assert response.json()["caption"] == ""

    def test_invalid_uuid_detail_is_404(self) -> None:
        alice = _auth_client("alice")
        assert alice.get(f"{POSTS_URL}not-a-uuid/").status_code == 404
