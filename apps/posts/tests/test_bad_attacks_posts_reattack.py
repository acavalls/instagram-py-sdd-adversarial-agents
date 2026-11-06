"""GBU re-attack tests for the posts API (add-posts, post-fix iteration).

Goals: (1) verify the BUG-001/BUG-002 fixes hold against bypass attempts
(list-endpoint media-URL leaks, clamp boundary at exactly 2**63-1 and one
over), (2) verify the fixes did not break owner flows, (3) fresh hostile
inputs on the remaining surface. Every test asserts behavior the delta
specs (openspec/changes/add-posts/specs/posts/spec.md) require.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia
from apps.posts.tests.test_bad_attacks_posts import (
    GIF_BYTES,
    auth_client,
    create_post,
    make_user,
)

pytestmark = pytest.mark.django_db

POSTS_URL = "/api/posts/"
MAX_I64 = 2**63 - 1


def make_media_file(name: str = "media.gif") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def create_post_with_media(owner: User, caption: str, media_name: str) -> Post:
    post = Post.objects.create(owner=owner, caption=caption)
    PostMedia.objects.create(post=post, image=make_media_file(media_name), order=0)
    return post


# ---------------------------------------------------------------------------
# BUG-001 bypass attempts: other paths to another user's post/media
# ---------------------------------------------------------------------------


def test_ratk001_list_endpoint_leaks_no_other_users_media_urls(api_client):
    """Bypass attempt for the BUG-001 fix: PostListSerializer adds
    first_image_url. Bob's listing must not contain Alice's post id,
    caption, or any of her media URLs."""
    alice = make_user("alice")
    bob = make_user("bob")
    create_post_with_media(alice, "alice secret caption", "alice-secret-media.gif")
    auth_client(api_client, bob)

    response = api_client.get(POSTS_URL)

    assert response.status_code == 200, response.content
    body = response.content.decode()
    assert "alice secret caption" not in body
    assert "alice-secret-media" not in body
    assert str(alice.posts.get().pk) not in body


def test_ratk002_detail_404_body_leaks_no_media_url(api_client):
    """The 404 body for a non-owner detail GET must not contain the post's
    media URL either (any leak of the URL is a visibility violation)."""
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post_with_media(alice, "alice secret", "alice-secret-media.gif")
    auth_client(api_client, bob)

    response = api_client.get(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 404
    assert b"alice-secret-media" not in response.content
    assert b"alice secret" not in response.content


def test_ratk003_non_owner_patch_and_delete_rejected_via_api(api_client):
    """Spec scenarios: non-owner PATCH/DELETE answer 403 with the ownership
    error and the post is untouched."""
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post(alice, caption="original")
    auth_client(api_client, bob)

    patch_response = api_client.patch(
        f"{POSTS_URL}{post.pk}/", {"caption": "hacked"}, format="json"
    )
    delete_response = api_client.delete(f"{POSTS_URL}{post.pk}/")

    assert patch_response.status_code == 403, patch_response.content
    assert patch_response.json() == {"error": "You can only edit your own posts"}
    assert delete_response.status_code == 403, delete_response.content
    assert delete_response.json() == {"error": "You can only delete your own posts"}
    post.refresh_from_db()
    assert post.caption == "original"


# ---------------------------------------------------------------------------
# BUG-002 bypass attempts: clamp boundary and one-over routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        f"limit={MAX_I64}&offset={MAX_I64}",  # exactly at the clamp bound
        f"limit={MAX_I64}",  # exact bound, default offset
        f"offset={MAX_I64}&limit=1",  # exact bound offset, tiny window
        f"limit={MAX_I64 + 1}",  # one over the signed 64-bit max
        f"limit={MAX_I64 * 3}&offset={MAX_I64 * 7}",  # far over, both params
    ],
)
def test_ratk004_clamp_boundaries_answer_200(api_client, query):
    alice = make_user("alice")
    create_post(alice, caption="mine")
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?{query}")

    assert response.status_code == 200, (query, response.status_code, response.content)


def test_ratk005_clamped_limit_still_returns_own_posts(api_client):
    """Clamping must not swallow the user's data: a limit one over the bound
    still returns the user's posts (window semantics intact)."""
    alice = make_user("alice")
    create_post(alice, caption="mine")
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?limit={MAX_I64 + 1}")

    assert response.status_code == 200, response.content
    assert [p["caption"] for p in response.json()] == ["mine"]


# ---------------------------------------------------------------------------
# Owner-flow regression risk from the GetPostUseCase change
# ---------------------------------------------------------------------------


def test_ratk006_owner_detail_returns_post_with_media(api_client):
    alice = make_user("alice")
    post = create_post_with_media(alice, "my caption", "mine.gif")
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}{post.pk}/")

    assert response.status_code == 200, response.content
    data = response.json()
    assert data["caption"] == "my caption"
    assert data["owner_username"] == "alice"
    assert data["media_count"] == 1
    assert data["media"][0]["order"] == 0


def test_ratk007_owner_patch_still_works(api_client):
    alice = make_user("alice")
    post = create_post(alice, caption="before")
    auth_client(api_client, alice)

    response = api_client.patch(f"{POSTS_URL}{post.pk}/", {"caption": "after"}, format="json")

    assert response.status_code == 200, response.content
    post.refresh_from_db()
    assert post.caption == "after"


# ---------------------------------------------------------------------------
# Fresh hostile inputs on the remaining surface
# ---------------------------------------------------------------------------


def test_ratk008_lone_surrogate_caption_never_500(api_client):
    """A JSON caption containing a lone UTF-16 surrogate is malformed text;
    it must be rejected or stored safely, never crash with a 500."""
    alice = make_user("alice")
    auth_client(api_client, alice)

    # Raw bytes: the lone surrogate cannot pass through the JSON renderer,
    # so the crafted body is sent directly to exercise the server side.
    response = api_client.post(
        POSTS_URL,
        data=b'{"caption": "bad \\ud800 caption"}',
        content_type="application/json",
    )

    assert response.status_code in (201, 400), (response.status_code, response.content)


def test_ratk009_control_characters_caption_stored_safely(api_client):
    alice = make_user("alice")
    auth_client(api_client, alice)
    caption = "line1\nline2\ttab\x07bell"

    response = api_client.post(POSTS_URL, {"caption": caption}, format="json")

    assert response.status_code == 201, response.content
    assert response.json()["caption"] == caption


def test_ratk010_repeated_limit_query_param_answers_200(api_client):
    """Repeated query params: Django's QueryDict.get takes the last value;
    either way the endpoint must answer 200 without crashing."""
    alice = make_user("alice")
    create_post(alice, caption="p0")
    create_post(alice, caption="p1")
    auth_client(api_client, alice)

    response = api_client.get(f"{POSTS_URL}?limit=1&limit=0")

    assert response.status_code == 200, response.content
    assert len(response.json()) == 0  # last value wins (limit=0 -> empty window)
