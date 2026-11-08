import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.posts.models import Post, PostMedia

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
POSTS_URL = "/api/posts/"

ERROR_POST_NOT_FOUND = "Post not found"
ERROR_EDIT_FORBIDDEN = "You can only edit your own posts"
ERROR_DELETE_FORBIDDEN = "You can only delete your own posts"


def _auth_client(username: str = "alice") -> APIClient:
    """A client authenticated with a JWT obtained from /api/auth/login/."""
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


def _image(name: str = "pic.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/png")


def _video(name: str = "clip.mp4") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"fake-video-bytes", content_type="video/mp4")


def _create_post(client: APIClient, caption: str = "hello", files: list | None = None):
    return client.post(
        POSTS_URL,
        {"caption": caption, "media": files or []},
        format="multipart",
    )


def _post_id(post: Post) -> str:
    return str(post.id)


@pytest.mark.django_db
class TestPostCreationAPI:
    def test_successful_api_creation(self) -> None:
        client = _auth_client()

        response = _create_post(
            client, caption="my caption", files=[_image("one.png"), _image("two.png")]
        )

        assert response.status_code == 201
        data = response.json()
        post = Post.objects.get(id=data["id"])
        assert post.owner.username == "alice"
        assert data["owner_username"] == "alice"
        assert data["caption"] == "my caption"
        assert data["media_count"] == 2
        assert [media["order"] for media in data["media"]] == [0, 1]
        assert all(media["media_type"] == "image" for media in data["media"])
        assert all(media["file"] for media in data["media"])
        assert PostMedia.objects.filter(post=post).count() == 2

    def test_api_creation_with_too_many_media_files(self) -> None:
        client = _auth_client()

        response = _create_post(client, files=[_image(f"{i}.png") for i in range(11)])

        assert response.status_code == 400
        assert response.json()["media"] == ["A post cannot have more than 10 media files"]
        assert not Post.objects.exists()

    def test_whitespace_only_caption_becomes_empty(self) -> None:
        client = _auth_client()

        response = _create_post(client, caption="   \n\t ")

        assert response.status_code == 201
        data = response.json()
        assert data["caption"] == ""
        assert Post.objects.get(id=data["id"]).caption == ""

    def test_caption_too_long_rejected(self) -> None:
        client = _auth_client()

        response = _create_post(client, caption="x" * 2201)

        assert response.status_code == 400
        assert not Post.objects.exists()


@pytest.mark.django_db
class TestPostListAPI:
    def test_api_list_of_own_posts(self) -> None:
        client = _auth_client()
        for index in range(3):
            _create_post(client, caption=f"post {index}")

        response = client.get(POSTS_URL)

        assert response.status_code == 200
        data = response.json()
        captions = [post["caption"] for post in data]
        assert captions == ["post 2", "post 1", "post 0"]
        assert all(post["owner_username"] == "alice" for post in data)

    def test_api_list_includes_first_image_thumbnail(self) -> None:
        client = _auth_client()
        _create_post(client, caption="with media", files=[_video("clip.mp4"), _image("pic.png")])
        _create_post(client, caption="without media")

        response = client.get(POSTS_URL)

        assert response.status_code == 200
        data = response.json()
        by_caption = {post["caption"]: post for post in data}
        with_media = by_caption["with media"]
        # The thumbnail is the first IMAGE media (order 1), not the first media file.
        assert with_media["first_image_url"].endswith("/media/post_media/pic.png")
        without_media = by_caption["without media"]
        assert without_media["first_image_url"] == ""

    def test_no_cross_user_listing(self) -> None:
        alice = _auth_client("alice")
        bob = _auth_client("bob")
        _create_post(alice, caption="alice secret")
        _create_post(bob, caption="bob secret")

        response = alice.get(POSTS_URL)

        assert response.status_code == 200
        captions = [post["caption"] for post in response.json()]
        assert captions == ["alice secret"]

    def test_pagination_window(self) -> None:
        client = _auth_client()
        created_ids = []
        for index in range(5):
            response = _create_post(client, caption=f"post {index}")
            created_ids.append(response.json()["id"])
        expected_order = list(reversed(created_ids))

        first_page = client.get(POSTS_URL, {"limit": 2, "offset": 0}).json()
        second_page = client.get(POSTS_URL, {"limit": 2, "offset": 2}).json()
        third_page = client.get(POSTS_URL, {"limit": 2, "offset": 4}).json()

        page_ids = [post["id"] for post in first_page + second_page + third_page]
        assert page_ids == expected_order
        assert len(set(page_ids)) == 5

    def test_invalid_pagination_rejected(self) -> None:
        client = _auth_client()

        response = client.get(POSTS_URL, {"limit": "banana"})

        assert response.status_code == 400
        assert response.json() == {"error": "Invalid pagination parameters"}

    def test_authentication_required(self) -> None:
        client = APIClient()

        response = client.get(POSTS_URL)

        # 403, not 401: SessionAuthentication (first in the defaults) does not
        # issue a WWW-Authenticate challenge for anonymous requests.
        assert response.status_code == 403


@pytest.mark.django_db
class TestPostDetailAPI:
    def test_existing_post_detail(self) -> None:
        client = _auth_client()
        response = _create_post(client, caption="detail me", files=[_image("pic.png")])
        post_id = response.json()["id"]

        response = client.get(f"{POSTS_URL}{post_id}/")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert data["caption"] == "detail me"
        assert data["media_count"] == 1
        assert data["media"][0]["media_type"] == "image"

    def test_unknown_post_detail(self) -> None:
        client = _auth_client()

        response = client.get(f"{POSTS_URL}{uuid.uuid4()}/")

        assert response.status_code == 404
        assert response.json() == {"error": ERROR_POST_NOT_FOUND}

    def test_owner_updates_caption_via_api(self) -> None:
        client = _auth_client()
        post_id = _create_post(client, caption="old caption").json()["id"]

        response = client.patch(f"{POSTS_URL}{post_id}/", {"caption": "new caption"}, format="json")

        assert response.status_code == 200
        assert response.json()["caption"] == "new caption"
        assert Post.objects.get(id=post_id).caption == "new caption"

    def test_non_owner_update_rejected(self) -> None:
        alice = _auth_client("alice")
        post_id = _create_post(alice, caption="alice post").json()["id"]
        bob = _auth_client("bob")

        response = bob.patch(f"{POSTS_URL}{post_id}/", {"caption": "bob was here"}, format="json")

        assert response.status_code == 403
        assert response.json() == {"error": ERROR_EDIT_FORBIDDEN}
        assert Post.objects.get(id=post_id).caption == "alice post"

    def test_owner_deletes_post_via_api(self) -> None:
        client = _auth_client()
        post_id = _create_post(client, files=[_image("pic.png")]).json()["id"]

        response = client.delete(f"{POSTS_URL}{post_id}/")

        assert response.status_code == 204
        assert not Post.objects.filter(id=post_id).exists()
        assert not PostMedia.objects.exists()

    def test_non_owner_deletion_rejected(self) -> None:
        alice = _auth_client("alice")
        post_id = _create_post(alice, caption="alice post").json()["id"]
        bob = _auth_client("bob")

        response = bob.delete(f"{POSTS_URL}{post_id}/")

        assert response.status_code == 403
        assert response.json() == {"error": ERROR_DELETE_FORBIDDEN}
        assert Post.objects.filter(id=post_id).exists()
