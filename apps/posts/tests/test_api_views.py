"""API view tests for the posts capability, named after the spec scenarios
they cover (tasks 3.1 and 3.2)."""

from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.posts.models import Post

pytestmark = pytest.mark.django_db

POSTS_URL = "/api/posts/"

RAW_PASSWORD = "sup3r-secret-pw"

# Minimal valid 1x1 transparent GIF, used as uploaded media content.
GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def make_user(**overrides: Any) -> User:
    data = {"username": "alice", "email": "alice@example.com", "password": RAW_PASSWORD}
    data.update(overrides)
    return User.objects.create_user(**data)


def make_media_file(name: str = "media.gif"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def auth_client(api_client: APIClient, user: User) -> APIClient:
    """Authenticate the client with a JWT access token for ``user``."""
    token = AccessToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


def test_successful_api_creation(api_client):
    """Spec scenario: Successful API creation — POST /api/posts/ with a
    caption and images answers 201 with the created post payload."""
    user = make_user()
    auth_client(api_client, user)

    response = api_client.post(
        POSTS_URL,
        {"caption": "my first post", "media": [make_media_file(), make_media_file("two.gif")]},
    )

    assert response.status_code == 201
    post = Post.objects.get(owner=user)
    assert post.caption == "my first post"
    data = response.json()
    assert data["id"] == str(post.pk)
    assert data["owner_username"] == "alice"
    assert data["caption"] == "my first post"
    assert data["media_count"] == 2
    assert [media["order"] for media in data["media"]] == [0, 1]
    assert all(media["media_type"] == "image" for media in data["media"])
    assert all(media["url"] for media in data["media"])

    # A caption-less post is also valid (media is not required either).
    bare = api_client.post(POSTS_URL, {})
    assert bare.status_code == 201
    assert bare.json()["caption"] == ""
    assert bare.json()["media_count"] == 0


def test_api_creation_with_too_many_media_files(api_client):
    """Spec scenario: API creation with too many media files — more than 10
    media files answer 400 with a validation error."""
    auth_client(api_client, make_user())
    files = {f"media_{index}": make_media_file(f"m{index}.gif") for index in range(11)}
    payload = {"media": list(files.values())}

    response = api_client.post(POSTS_URL, payload)

    assert response.status_code == 400
    assert "media" in response.json()
    assert Post.objects.count() == 0

    # Exactly 10 files are accepted (fresh files: the ones above were
    # consumed by the rejected request's parsing).
    fresh_files = [make_media_file(f"ok{index}.gif") for index in range(10)]
    ok = api_client.post(POSTS_URL, {"media": fresh_files})
    assert ok.status_code == 201


def test_api_list_of_own_posts(api_client):
    """Spec scenario: API list of own posts — GET /api/posts/ returns the
    authenticated user's own posts, newest first."""
    user = make_user()
    auth_client(api_client, user)
    first = Post.objects.create(owner=user, caption="first")
    second = Post.objects.create(owner=user, caption="second")

    response = api_client.get(POSTS_URL)

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [str(second.pk), str(first.pk)]
    assert data[0]["caption"] == "second"
    assert data[0]["owner_username"] == "alice"
    assert "first_image_url" in data[0]


def test_no_cross_user_listing(api_client):
    """Spec scenario: No cross-user listing — while other users have posts,
    the listing returns only the authenticated user's own posts."""
    user = make_user()
    auth_client(api_client, user)
    stranger = make_user(username="bob", email="bob@example.com")
    Post.objects.create(owner=stranger, caption="not mine")
    own = Post.objects.create(owner=user, caption="mine")

    response = api_client.get(POSTS_URL)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(own.pk)]
    # The other user's account is untouched by the listing.
    assert Post.objects.filter(owner=stranger).count() == 1


def test_pagination_window(api_client):
    """Spec scenario: Pagination window — limit/offset returns only the
    requested window, without duplicates across pages."""
    user = make_user()
    auth_client(api_client, user)
    posts = [Post.objects.create(owner=user, caption=f"post {index}") for index in range(3)]

    page_one = api_client.get(POSTS_URL, {"limit": 2, "offset": 0})
    page_two = api_client.get(POSTS_URL, {"limit": 2, "offset": 2})

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    ids_one = [item["id"] for item in page_one.json()]
    ids_two = [item["id"] for item in page_two.json()]
    # Newest first, no duplicates across the pages.
    assert ids_one == [str(posts[2].pk), str(posts[1].pk)]
    assert ids_two == [str(posts[0].pk)]
    assert not set(ids_one) & set(ids_two)

    # Invalid pagination values answer 400.
    assert api_client.get(POSTS_URL, {"limit": "not-a-number"}).status_code == 400
    assert api_client.get(POSTS_URL, {"offset": -1}).status_code == 400


def test_existing_post_detail(api_client):
    """Spec scenario: Existing post detail — GET /api/posts/<uuid>/ for an
    existing post answers 200 with the post data including its media."""
    user = make_user()
    auth_client(api_client, user)
    post = Post.objects.create(owner=user, caption="look at this")
    post.media.create(image=make_media_file("detail.gif"), media_type="image", order=0)

    response = api_client.get(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(post.pk)
    assert data["caption"] == "look at this"
    assert data["owner_username"] == "alice"
    assert data["media_count"] == 1
    assert data["media"][0]["order"] == 0
    assert data["media"][0]["media_type"] == "image"


def test_unknown_post_detail(api_client):
    """Spec scenario: Unknown post detail — an unknown identifier answers
    404 with the error "Post not found"."""
    import uuid

    auth_client(api_client, make_user())

    response = api_client.get(f"{POSTS_URL}{uuid.uuid4()}/")

    assert response.status_code == 404
    assert response.json() == {"error": "Post not found"}


def test_owner_updates_caption_via_api(api_client):
    """Spec scenario: Owner updates caption via API — PATCH with a new
    caption answers 200 with the updated post."""
    owner = make_user()
    auth_client(api_client, owner)
    post = Post.objects.create(owner=owner, caption="before")

    response = api_client.patch(f"{POSTS_URL}{post.pk}/", {"caption": "after"})

    assert response.status_code == 200
    data = response.json()
    assert data["caption"] == "after"
    assert Post.objects.get(pk=post.pk).caption == "after"


def test_non_owner_update_rejected(api_client):
    """Spec scenario: Non-owner update rejected — a non-owner PATCH answers
    403 with the exact ownership error and the caption is unchanged."""
    owner = make_user()
    post = Post.objects.create(owner=owner, caption="before")
    auth_client(api_client, make_user(username="bob", email="bob@example.com"))

    response = api_client.patch(f"{POSTS_URL}{post.pk}/", {"caption": "hacked"})

    assert response.status_code == 403
    assert response.json() == {"error": "You can only edit your own posts"}
    assert Post.objects.get(pk=post.pk).caption == "before"

    # A missing or blank caption is a 400 validation error, not an update.
    assert api_client.patch(f"{POSTS_URL}{post.pk}/", {}).status_code == 400
    assert api_client.patch(f"{POSTS_URL}{post.pk}/", {"caption": ""}).status_code == 400
    assert Post.objects.get(pk=post.pk).caption == "before"


def test_owner_deletes_post_via_api(api_client):
    """Spec scenario: Owner deletes post via API — DELETE answers 204 and
    the post and its media no longer exist."""
    owner = make_user()
    auth_client(api_client, owner)
    post = Post.objects.create(owner=owner, caption="doomed")
    post.media.create(image=make_media_file("doomed.gif"), media_type="image", order=0)

    response = api_client.delete(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 204
    assert response.content == b""
    assert not Post.objects.filter(pk=post.pk).exists()
    assert post.media.count() == 0


def test_non_owner_deletion_rejected(api_client):
    """Spec scenario: Non-owner deletion rejected — a non-owner DELETE
    answers 403 with the exact ownership error and the post still exists."""
    owner = make_user()
    post = Post.objects.create(owner=owner, caption="survivor")
    auth_client(api_client, make_user(username="bob", email="bob@example.com"))

    response = api_client.delete(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 403
    assert response.json() == {"error": "You can only delete your own posts"}
    assert Post.objects.filter(pk=post.pk).exists()
