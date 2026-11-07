"""GBU adversarial attack tests for the posts web (HTMX) endpoints
(add-posts change).

Every test asserts the behavior the delta specs require, so a failure is a
demonstrated defect. The web surface: POST /web/posts/create/,
GET /web/posts/<uuid>/edit-form/, GET /web/posts/<uuid>/cancel-edit/,
POST /web/posts/<uuid>/submit-edit/, POST /web/posts/<uuid>/delete/ and the
feed page /web/feed/.
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.posts.models import Post

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"


def make_user(username: str = "alice", email: str | None = None) -> User:
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=RAW_PASSWORD,
    )


def login(client: Client, user: User) -> None:
    client.force_login(user)


def create_post(owner: User, caption: str = "seed caption") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


# ---------------------------------------------------------------------------
# ATK-W01: anonymous access to every web post endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs,method",
    [
        ({"path": "/web/posts/create/"}, "post"),
        ({"pk": "00000000-0000-0000-0000-000000000000", "url_name": "post-edit-form"}, "get"),
        ({"pk": "00000000-0000-0000-0000-000000000000", "url_name": "post-cancel-edit"}, "get"),
        ({"pk": "00000000-0000-0000-0000-000000000000", "url_name": "post-submit-edit"}, "post"),
        ({"pk": "00000000-0000-0000-0000-000000000000", "url_name": "post-delete"}, "post"),
    ],
)
def test_atk_w01_anonymous_is_redirected_to_login(kwargs, method):
    client = Client()
    url = (
        kwargs["path"]
        if "path" in kwargs
        else reverse("web:" + kwargs["url_name"], kwargs={"pk": kwargs["pk"]})
    )
    response = getattr(client, method)(url, {"caption": "x"} if method == "post" else {})
    assert response.status_code == 302, response.status_code
    assert response.url.startswith("/web/login/")


def test_atk_w01b_anonymous_feed_redirects():
    client = Client()
    response = client.get("/web/feed/")
    assert response.status_code == 302
    assert response["Location"].startswith("/web/login/")  # type: ignore[index]


# ---------------------------------------------------------------------------
# ATK-W02: CSRF enforcement on state-changing web endpoints
# ---------------------------------------------------------------------------


def test_atk_w02_create_post_requires_csrf_token():
    alice = make_user("alice")
    client = Client(enforce_csrf_checks=True)
    login(client, alice)

    response = client.post("/web/posts/create/")

    assert response.status_code == 403, response.status_code
    assert Post.objects.filter(owner=alice).count() == 0


def test_atk_w02b_delete_requires_csrf_token():
    alice = make_user("alice")
    post = create_post(alice)
    client = Client(enforce_csrf_checks=True)
    login(client, alice)

    response = client.post(reverse("web:post-delete", kwargs={"pk": post.pk}))

    assert response.status_code == 403, response.status_code
    assert Post.objects.filter(pk=post.pk).exists()


# ---------------------------------------------------------------------------
# ATK-W03: cross-user attacks on the inline edit / delete endpoints
# ---------------------------------------------------------------------------


def test_atk_w03a_non_owner_cannot_render_edit_form():
    """BUG-001 repro (web side). Spec requirement 'Post visibility': posts
    are visible only through their owner's content listings. Rendering the
    edit form (and its caption) for another user's post leaks the post."""
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post(alice, caption="alice private")
    client = Client()
    login(client, bob)

    response = client.get(reverse("web:post-edit-form", kwargs={"pk": post.pk}))

    assert response.status_code == 200
    assert b"alice private" not in response.content, (
        "the edit form must not render another user's post caption"
    )


def test_atk_w03b_non_owner_cancel_edit_leaks_nothing():
    bob = make_user("bob")
    alice = make_user("alice")
    post = create_post(alice, caption="alice private")
    client = Client()
    login(client, bob)

    response = client.get(reverse("web:post-cancel-edit", kwargs={"pk": post.pk}))

    assert b"alice private" not in response.content


def test_atk_w03c_non_owner_submit_edit_rejected_and_post_untouched():
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post(alice, caption="original")
    client = Client()
    login(client, bob)

    response = client.post(
        reverse("web:post-submit-edit", kwargs={"pk": post.pk}), {"caption": "hacked"}
    )

    assert response.status_code == 200
    assert b"You can only edit your own posts" in response.content
    post.refresh_from_db()
    assert post.caption == "original"


def test_atk_w03d_non_owner_delete_rejected_and_post_survives():
    alice = make_user("alice")
    bob = make_user("bob")
    post = create_post(alice)
    client = Client()
    login(client, bob)

    response = client.post(reverse("web:post-delete", kwargs={"pk": post.pk}))

    assert response.status_code == 200
    assert b"You can only delete your own posts" in response.content
    assert Post.objects.filter(pk=post.pk).exists()


# ---------------------------------------------------------------------------
# ATK-W04: hostile sequences and malformed captions on the web endpoints
# ---------------------------------------------------------------------------


def test_atk_w04a_submit_edit_caption_over_limit_error_toast_no_500():
    alice = make_user("alice")
    post = create_post(alice, caption="short")
    client = Client()
    login(client, alice)

    response = client.post(
        reverse("web:post-submit-edit", kwargs={"pk": post.pk}), {"caption": "x" * 2201}
    )

    assert response.status_code == 200
    assert b"2200" in response.content
    post.refresh_from_db()
    assert post.caption == "short"


def test_atk_w04b_submit_edit_on_deleted_post_error_toast_no_500():
    alice = make_user("alice")
    post = create_post(alice)
    post_id = post.pk
    post.delete()
    client = Client()
    login(client, alice)

    response = client.post(
        reverse("web:post-submit-edit", kwargs={"pk": post_id}), {"caption": "zombie"}
    )

    assert response.status_code == 200
    assert b"Post not found" in response.content


def test_atk_w04c_edit_form_and_cancel_on_deleted_post_return_empty():
    alice = make_user("alice")
    post = create_post(alice)
    post_id = post.pk
    post.delete()
    client = Client()
    login(client, alice)

    for url_name in ("post-edit-form", "post-cancel-edit"):
        response = client.get(reverse("web:" + url_name, kwargs={"pk": post_id}))
        assert response.status_code == 200
        assert response.content.strip() == b""


def test_atk_w04d_get_on_delete_endpoint_is_405():
    alice = make_user("alice")
    post = create_post(alice)
    client = Client()
    login(client, alice)

    response = client.get(reverse("web:post-delete", kwargs={"pk": post.pk}))

    assert response.status_code == 405
    assert Post.objects.filter(pk=post.pk).exists()


def test_atk_w04e_garbage_uuid_routes_404_not_500():
    alice = make_user("alice")
    client = Client()
    login(client, alice)

    response = client.get("/web/posts/not-a-uuid/edit-form/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# ATK-W05: feed page attacks (pagination parameter abuse)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("page_param", ["abc", "1.5", "-3", "0", "99999999999999999999", ""])
def test_atk_w05a_feed_survives_hostile_page_params(page_param):
    alice = make_user("alice")
    for i in range(3):
        create_post(alice, caption=f"p{i}")
    client = Client()
    login(client, alice)

    response = client.get(f"/web/feed/?page={page_param}")

    assert response.status_code == 200, (page_param, response.status_code)


def test_atk_w05b_feed_shows_only_followed_users_posts():
    # Social delta: the home feed shows the followed users' posts — never the
    # visitor's own posts and never posts from users they do not follow.
    from apps.social.services import FollowService

    alice = make_user("alice")
    bob = make_user("bob")
    carol = make_user("carol")
    FollowService().follow(follower=alice, following=bob)
    create_post(bob, caption="bob visible")
    create_post(carol, caption="carol secret")
    create_post(alice, caption="alice own")
    client = Client()
    login(client, alice)

    response = client.get("/web/feed/")

    assert response.status_code == 200
    assert b"bob visible" in response.content
    assert b"carol secret" not in response.content
    assert b"alice own" not in response.content


def test_atk_w05c_feed_paginates_without_duplicates():
    from django.utils import timezone

    from apps.posts.models import Post as PostModel
    from apps.social.services import FollowService

    alice = make_user("alice")
    bob = make_user("bob")
    FollowService().follow(follower=alice, following=bob)
    posts = [create_post(bob, caption=f"page-post-{i}") for i in range(5)]
    tied = timezone.now()
    PostModel.objects.filter(pk__in=[p.pk for p in posts]).update(created_at=tied)
    client = Client()
    login(client, alice)

    seen: list[str] = []
    for page in (1, 2, 3, 4, 5):
        response = client.get(f"/web/feed/?page={page}")
        assert response.status_code == 200
        content = response.content.decode()
        for i in range(5):
            if f"page-post-{i}" in content:
                seen.append(f"page-post-{i}")

    assert len(set(seen)) == len(seen) == 5, f"duplicates or skips across pages: {sorted(seen)}"


# ---------------------------------------------------------------------------
# ATK-W06: web creation flow
# ---------------------------------------------------------------------------


def test_atk_w06_create_post_toast_and_placeholder():
    alice = make_user("alice")
    client = Client()
    login(client, alice)

    response = client.post("/web/posts/create/", follow=True)

    assert response.status_code == 200
    assert b"Post created!" in response.content
    post = Post.objects.get(owner=alice)
    assert post.caption != ""
    assert post.media.count() == 1


def test_atk_w06b_create_then_immediate_delete_roundtrip():
    alice = make_user("alice")
    client = Client()
    login(client, alice)

    client.post("/web/posts/create/")
    post = Post.objects.get(owner=alice)
    response = client.post(reverse("web:post-delete", kwargs={"pk": post.pk}))

    assert response.status_code == 200
    assert b"Post deleted!" in response.content
    assert Post.objects.count() == 0


def test_atk_w06c_owner_can_edit_own_post_via_web():
    alice = make_user("alice")
    post = create_post(alice, caption="before")
    client = Client()
    login(client, alice)

    response = client.post(
        reverse("web:post-submit-edit", kwargs={"pk": post.pk}), {"caption": "after"}
    )

    assert response.status_code == 200
    assert b"Post updated!" in response.content
    post.refresh_from_db()
    assert post.caption == "after"
