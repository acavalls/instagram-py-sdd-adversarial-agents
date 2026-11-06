"""GBU re-attack tests for the posts web (HTMX) endpoints (post-fix iteration).

Focus: regression risk of the BUG-001 fix on VALID owners (edit-form /
cancel-edit must still render for the owner) and BUG-002 bypass routes
through the feed page. Every test asserts behavior the delta specs require.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.posts.models import Post, PostMedia
from apps.web.tests.test_bad_attacks_posts_web import create_post, login, make_user

pytestmark = pytest.mark.django_db

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)

MAX_I64 = 2**63 - 1


def create_post_with_media(owner: User, caption: str, media_name: str) -> Post:
    post = Post.objects.create(owner=owner, caption=caption)
    PostMedia.objects.create(
        post=post,
        image=SimpleUploadedFile(media_name, GIF_BYTES, content_type="image/gif"),
        order=0,
    )
    return post


# ---------------------------------------------------------------------------
# BUG-001 fix regression risk: owner flows must keep working
# ---------------------------------------------------------------------------


def test_ratkw01_owner_edit_form_still_renders_caption():
    alice = make_user("alice")
    post = create_post(alice, caption="my own caption")
    client = Client()
    login(client, alice)

    response = client.get(reverse("web:post-edit-form", kwargs={"pk": post.pk}))

    assert response.status_code == 200
    assert b"my own caption" in response.content


def test_ratkw02_owner_cancel_edit_still_returns_the_card():
    alice = make_user("alice")
    post = create_post(alice, caption="my own caption")
    client = Client()
    login(client, alice)

    response = client.get(reverse("web:post-cancel-edit", kwargs={"pk": post.pk}))

    assert response.status_code == 200
    assert b"my own caption" in response.content
    assert b"post-card" in response.content


def test_ratkw03_owner_feed_renders_own_media_url():
    alice = make_user("alice")
    create_post_with_media(alice, "with media", "mine.gif")
    client = Client()
    login(client, alice)

    response = client.get("/web/feed/")

    assert response.status_code == 200
    assert b"with media" in response.content
    # Storage may suffix the filename, so assert on the served path prefix.
    assert b"/media/post_media/" in response.content


# ---------------------------------------------------------------------------
# BUG-002 bypass attempts through the web feed pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "page_param",
    [
        str(MAX_I64),  # offset = (MAX-1)*10 overflows the signed 64-bit max
        str(2**62),  # offset far over the clamp bound
        "922337203685477581",  # offset just under the clamp bound
    ],
)
def test_ratkw04_feed_huge_pages_answer_200(page_param):
    alice = make_user("alice")
    create_post(alice, caption="mine")
    client = Client()
    login(client, alice)

    response = client.get(f"/web/feed/?page={page_param}")

    assert response.status_code == 200, (page_param, response.status_code)


# ---------------------------------------------------------------------------
# Cross-user media-URL leak through the feed page (BUG-001 bypass attempt)
# ---------------------------------------------------------------------------


def test_ratkw05_feed_leaks_no_other_users_media_urls():
    alice = make_user("alice")
    bob = make_user("bob")
    create_post_with_media(alice, "alice secret", "alice-secret-media.gif")
    client = Client()
    login(client, bob)

    response = client.get("/web/feed/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "alice secret" not in body
    assert "alice-secret-media" not in body
    assert str(alice.posts.get().pk) not in body
