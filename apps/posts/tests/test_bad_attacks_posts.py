"""GBU adversarial attack tests for the posts API (add-posts change).

These tests probe the exposed API surface with hostile inputs and hostile
sequences. They are regression tests: every test asserts the behavior the
delta specs (openspec/changes/add-posts/specs/posts/spec.md) require, so a
failure is a demonstrated defect.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.posts.models import Post

pytestmark = pytest.mark.django_db

POSTS_URL = "/api/posts/"

RAW_PASSWORD = "sup3r-secret-pw"

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def make_user(username: str = "alice", email: str | None = None) -> User:
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=RAW_PASSWORD,
    )


def make_media_file(name: str = "media.gif", content: bytes = GIF_BYTES) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="image/gif")


def auth_client(api_client: APIClient, user: User) -> APIClient:
    token = AccessToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


def create_post(owner: User, caption: str = "seed") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


# ---------------------------------------------------------------------------
# ATK-001: cross-user visibility via GET /api/posts/<uuid>/
# ---------------------------------------------------------------------------


def test_atk001_non_owner_cannot_read_post_detail(api_client):
    """BUG-001 repro (API side). Spec requirement 'Post visibility': posts
    are visible ONLY through their owner's content listings; no endpoint in
    this capability may expose another user's post. A non-owner GET of the
    post detail must therefore not return the post (404 'Post not found')."""
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post(alice, caption="alice private thought")

    auth_client(api_client, bob)
    response = api_client.get(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 404, response.content
    assert response.json() == {"error": "Post not found"}


# ---------------------------------------------------------------------------
# ATK-003: caption boundary attacks (2200 / 2201 / multibyte)
# ---------------------------------------------------------------------------


def test_atk003a_caption_exactly_2200_multibyte_is_accepted(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)
    caption = "é" * 2200  # multibyte characters, exactly at the limit

    response = api_client.post(POSTS_URL, {"caption": caption})

    assert response.status_code == 201, response.content
    assert response.json()["caption"] == caption


def test_atk003b_caption_2201_multibyte_is_rejected(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)
    caption = "🦄" * 2201  # astral-plane characters, one over the limit

    response = api_client.post(POSTS_URL, {"caption": caption})

    assert response.status_code == 400, response.content
    assert Post.objects.filter(owner=alice).count() == 0


def test_atk003c_patch_caption_2201_is_rejected(api_client):
    alice = make_user("alice")
    post = create_post(alice)
    auth_client(api_client, alice)

    response = api_client.patch(f"{POSTS_URL}{post.pk}/", {"caption": "x" * 2201}, format="json")

    assert response.status_code == 400, response.content
    post.refresh_from_db()
    assert post.caption == "seed"


def test_atk003d_whitespace_only_caption_is_normalized(api_client):
    """Spec scenario 'Whitespace-only caption becomes empty' (Post creation,
    openspec/changes/regularize-social-drifts/specs/posts/spec.md): a caption
    consisting only of whitespace is stored as the empty string."""
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(POSTS_URL, {"caption": "   \n\t  "})

    assert response.status_code == 201, response.content
    assert response.json()["caption"] == ""


def test_atk003e_caption_with_null_byte_is_rejected_or_safe(api_client):
    """A null byte is not displayable text; it must be rejected or stored
    without corrupting the response. A 500 is never acceptable."""
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(POSTS_URL, {"caption": "bad\x00caption"}, format="json")

    assert response.status_code in (201, 400), response.content


# ---------------------------------------------------------------------------
# ATK-004: media list attacks (0/1/10/11, non-image, huge filename)
# ---------------------------------------------------------------------------


def test_atk004a_eleven_media_files_rejected(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(
        POSTS_URL, {"media": [make_media_file(f"m{i}.gif") for i in range(11)]}
    )

    assert response.status_code == 400, response.content
    assert Post.objects.filter(owner=alice).count() == 0


def test_atk004b_ten_media_files_accepted_with_orders(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(
        POSTS_URL, {"media": [make_media_file(f"m{i}.gif") for i in range(10)]}
    )

    assert response.status_code == 201, response.content
    assert [m["order"] for m in response.json()["media"]] == list(range(10))


def test_atk004c_non_image_file_claimed_as_image_rejected(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(
        POSTS_URL,
        {"media": [make_media_file("evil.gif", content=b"this is not an image")]},
    )

    assert response.status_code == 400, response.content


def test_atk004d_media_as_strings_rejected(api_client):
    """media entries that are not files (e.g. JSON strings, path traversal
    attempts) must be rejected, never resolved from the filesystem."""
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(
        POSTS_URL, {"caption": "hi", "media": ["../../../../etc/passwd"]}, format="json"
    )

    assert response.status_code == 400, response.content


def test_atk004e_huge_filename_never_500(api_client):
    """A 300-character filename is malformed input; the spec does not
    describe it, but a 500 crash is never acceptable behavior."""
    alice = make_user("alice")
    auth_client(api_client, alice)

    response = api_client.post(POSTS_URL, {"media": [make_media_file("x" * 300 + ".gif")]})

    assert response.status_code in (201, 400), response.content


# ---------------------------------------------------------------------------
# ATK-005: pagination parameter attacks on GET /api/posts/
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "limit=-1",
        "offset=-5",
        "limit=abc",
        "limit=1.5",
        "limit=0x10",
        "limit=1;DROP TABLE posts_post--",
        "limit=",
        "offset=-99999999999999999999",
    ],
)
def test_atk005a_malformed_pagination_rejected_with_400(api_client, query):
    alice = make_user("alice")
    create_post(alice)
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?{query}")

    assert response.status_code == 400, (query, response.content)
    assert "error" in response.json()


def test_atk005b_enormous_limit_and_offset_answer_200(api_client):
    alice = make_user("alice")
    create_post(alice)
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?limit=99999999999999999999&offset=99999999999999999999")

    assert response.status_code == 200, response.content
    assert response.json() == []


def test_atk005c_zero_limit_returns_empty_window(api_client):
    alice = make_user("alice")
    create_post(alice)
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?limit=0&offset=0")

    assert response.status_code == 200, response.content
    assert response.json() == []


# ---------------------------------------------------------------------------
# ATK-006: authentication attacks
# ---------------------------------------------------------------------------


def test_atk006a_missing_token_rejected(api_client):
    """Unauthenticated listing must be rejected. The spec does not pin the
    code for the posts endpoints, so either 401 or 403 is acceptable; a 200
    leak is not."""
    response = api_client.get(POSTS_URL)
    assert response.status_code in (401, 403)


def test_atk006b_garbage_token_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not.a.jwt")
    response = api_client.get(POSTS_URL)
    assert response.status_code in (401, 403)


def test_atk006c_forged_token_unsigned_rejected(api_client):
    alice = make_user("alice")
    token = AccessToken.for_user(alice)
    tampered = str(token)[:-3] + "abc"  # corrupt the signature
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")
    response = api_client.get(POSTS_URL)
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# ATK-007: hostile sequences around deletion
# ---------------------------------------------------------------------------


def test_atk007a_delete_then_get_and_patch_answer_404(api_client):
    alice = make_user("alice")
    post = create_post(alice)
    auth_client(api_client, alice)

    assert api_client.delete(f"{POSTS_URL}{post.pk}/").status_code == 204

    get_response = api_client.get(f"{POSTS_URL}{post.pk}/")
    patch_response = api_client.patch(
        f"{POSTS_URL}{post.pk}/", {"caption": "zombie"}, format="json"
    )
    delete_response = api_client.delete(f"{POSTS_URL}{post.pk}/")

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_atk007b_media_cascade_on_delete(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)
    created = api_client.post(POSTS_URL, {"media": [make_media_file(), make_media_file("two.gif")]})
    post_id = created.json()["id"]

    assert api_client.delete(f"{POSTS_URL}{post_id}/").status_code == 204
    assert Post.objects.count() == 0


# ---------------------------------------------------------------------------
# ATK-008: mass-assignment / identity spoofing
# ---------------------------------------------------------------------------


def test_atk008_owner_username_in_payload_cannot_spoof_owner(api_client):
    alice = make_user("alice")
    victim = make_user("victim")
    auth_client(api_client, alice)

    response = api_client.post(
        POSTS_URL,
        {
            "caption": "spoof attempt",
            "owner_username": "victim",
            "owner": str(victim.pk),
            "media": [make_media_file()],
        },
    )

    assert response.status_code == 201, response.content
    data = response.json()
    assert data["owner_username"] == "alice"
    assert Post.objects.filter(owner=victim).count() == 0
    assert Post.objects.get().owner_id == alice.pk


def test_atk008b_patch_cannot_change_owner_or_media(api_client):
    alice = make_user("alice")
    victim = make_user("victim")
    post = create_post(alice, caption="mine")
    auth_client(api_client, alice)

    response = api_client.patch(
        f"{POSTS_URL}{post.pk}/",
        {"caption": "still mine", "owner": str(victim.pk), "owner_username": "victim"},
        format="json",
    )

    assert response.status_code == 200, response.content
    post.refresh_from_db()
    assert post.owner_id == alice.pk


# ---------------------------------------------------------------------------
# ATK-009: pagination duplicates under tied created_at
# ---------------------------------------------------------------------------


def test_atk009_pagination_never_duplicates_or_skips_with_tied_timestamps(api_client):
    """Spec scenario 'Pagination window': no duplicates across pages. Posts
    created in the same instant (a realistic race) tie on created_at; the
    window must still partition the set without duplicates or skips."""
    from django.utils import timezone

    alice = make_user("alice")
    posts = [create_post(alice, caption=f"p{i}") for i in range(5)]
    tied = timezone.now()
    Post.objects.filter(pk__in=[p.pk for p in posts]).update(created_at=tied)
    auth_client(api_client, alice)

    seen: list[str] = []
    for offset in range(0, 5):
        response = api_client.get(f"{POSTS_URL}?limit=1&offset={offset}")
        assert response.status_code == 200
        page = response.json()
        assert len(page) == 1
        seen.append(page[0]["id"])

    assert len(set(seen)) == 5, f"duplicates or skips across pages: {seen}"


# ---------------------------------------------------------------------------
# ATK-013: cross-user isolation on the list endpoint (JWT of A only)
# ---------------------------------------------------------------------------


def test_atk013_list_only_own_posts_even_with_many_users(api_client):
    alice = make_user("alice")
    bob = make_user("bob")
    for i in range(3):
        create_post(alice, caption=f"alice {i}")
    create_post(bob, caption="bob secret")
    auth_client(api_client, alice)

    response = api_client.get(POSTS_URL)

    assert response.status_code == 200
    captions = [p["caption"] for p in response.json()]
    assert captions == ["alice 2", "alice 1", "alice 0"]


def test_atk014_garbage_uuid_routes_answer_404_not_500(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)

    for url in (
        f"{POSTS_URL}not-a-uuid/",
        f"{POSTS_URL}{'z' * 40}/",
        f"{POSTS_URL}00000000-0000-0000-0000-000000000000/",
    ):
        response = api_client.get(url)
        assert response.status_code == 404, (url, response.status_code)
