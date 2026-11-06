"""Web post view tests, named after the spec scenarios they cover
(task group 4, apps/web/post_views.py + apps/web/views.py:feed)."""

import uuid
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.posts.models import CAPTION_MAX_LENGTH, Post
from apps.web.post_views import PLACEHOLDER_CAPTIONS, PLACEHOLDER_GIF_BYTES

pytestmark = pytest.mark.django_db

FEED_URL = "/web/feed/"
CREATE_URL = "/web/posts/create/"
RAW_PASSWORD = "sup3r-secret-pw"


def make_user(**overrides: Any) -> User:
    data = {"username": "alice", "email": "alice@example.com", "password": RAW_PASSWORD}
    data.update(overrides)
    return User.objects.create_user(**data)


def make_post(owner: User, caption: str = "a caption") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def make_media_file(name: str = "media.gif") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, PLACEHOLDER_GIF_BYTES, content_type="image/gif")


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


# --- Spec scenario: Successful web creation ---------------------------------


def test_successful_web_creation(client):
    """Spec scenario: Successful web creation — POST /web/posts/create/
    creates a placeholder post (random caption from the app's caption list +
    generated 1x1 GIF) and confirms with the "Post created!" toast."""
    user = make_user()
    client.force_login(user)

    response = client.post(CREATE_URL)

    assert response.status_code == 302
    assert response.url == FEED_URL
    post = Post.objects.get(owner=user)
    assert post.caption in PLACEHOLDER_CAPTIONS
    media = post.media.first()
    assert media is not None
    assert media.media_type == "image"
    assert media.order == 0
    with media.image.open() as stored:
        assert stored.read() == PLACEHOLDER_GIF_BYTES
    assert "Post created!" in shown_messages(response)


def test_web_post_actions_require_login(client):
    """The web post endpoints are login-required: anonymous requests are
    redirected to the login page and nothing changes."""
    post = make_post(make_user())

    create_response = client.post(CREATE_URL)
    assert create_response.status_code == 302
    assert create_response.url.startswith("/web/login/")

    edit_response = client.get(f"/web/posts/{post.pk}/edit-form/")
    assert edit_response.status_code == 302
    assert edit_response.url.startswith("/web/login/")

    delete_response = client.post(f"/web/posts/{post.pk}/delete/")
    assert delete_response.status_code == 302
    assert delete_response.url.startswith("/web/login/")
    assert Post.objects.filter(pk=post.pk).exists()


# --- Spec scenario: Personal feed on the feed page ---------------------------


def test_personal_feed_on_the_feed_page(client):
    """Spec scenario: Personal feed on the feed page — the feed page shows the
    logged-in user's own posts as post cards (media, caption, owner,
    timestamp), newest first, and never another user's posts."""
    user = make_user()
    other = make_user(username="bob", email="bob@example.com")
    older = make_post(user, "older post")
    newer = make_post(user, "newer post")
    make_post(other, "bob secret post")
    # Force a clear creation order (auto_now_add timestamps are equal within
    # the same test tick).
    Post.objects.filter(pk=older.pk).update(created_at="2024-01-01T10:00:00Z")
    Post.objects.filter(pk=newer.pk).update(created_at="2024-06-01T10:00:00Z")

    client.force_login(user)
    response = client.get(FEED_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert "newer post" in content
    assert "older post" in content
    assert "bob secret post" not in content
    # Newest first: the newer caption appears before the older one.
    assert content.index("newer post") < content.index("older post")
    # Cards expose owner and timestamp.
    assert "alice" in content
    assert "post-card" in content


def test_personal_feed_renders_media_images(client):
    """The post cards render the media image through MEDIA_URL."""
    user = make_user()
    from apps.posts.services import PostService

    PostService().create(owner=user, caption="with media", media_files=[make_media_file()])

    client.force_login(user)
    response = client.get(FEED_URL)

    content = response.content.decode()
    assert "with media" in content
    assert "media/post_media/" in content
    assert "<img" in content


def test_personal_feed_pagination_window(client):
    """Spec scenario: Pagination window (web path) — a page returns only the
    requested window without duplicates across pages."""
    user = make_user()
    for index in range(12):
        post = make_post(user, f"post number {index}")
        Post.objects.filter(pk=post.pk).update(created_at=f"2024-01-{index + 1:02d}T10:00:00Z")

    client.force_login(user)
    first_page = client.get(FEED_URL)
    second_page = client.get(FEED_URL, {"page": 2})

    first_content = first_page.content.decode()
    second_content = second_page.content.decode()
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    # 12 posts, page size 10: page 1 holds the 10 newest, page 2 the last 2.
    assert first_content.count("post number") == 10
    assert second_content.count("post number") == 2
    assert "post number 11" in first_content  # newest
    assert "post number 0" not in first_content  # oldest is on page 2
    assert "post number 0" in second_content
    assert 'href="?page=2"' in first_content  # next control
    assert 'href="?page=1"' in second_content  # previous control


# --- Spec scenario: Inline web edit ------------------------------------------


def test_inline_web_edit(client):
    """Spec scenario: Inline web edit — submitting the inline edit form
    updates the caption, closes the form and shows the "Post updated!" toast."""
    user = make_user()
    post = make_post(user, "before edit")
    client.force_login(user)

    form_response = client.get(f"/web/posts/{post.pk}/edit-form/")
    assert form_response.status_code == 200
    form_content = form_response.content.decode()
    assert 'name="caption"' in form_content
    assert "before edit" in form_content

    submit_response = client.post(f"/web/posts/{post.pk}/submit-edit/", {"caption": "after edit"})
    assert submit_response.status_code == 200
    content = submit_response.content.decode()
    assert "Post updated!" in content
    assert "after edit" in content
    assert 'name="caption"' not in content  # the form is closed
    post.refresh_from_db()
    assert post.caption == "after edit"


# --- Spec scenario: Cancel inline edit ---------------------------------------


def test_cancel_inline_edit(client):
    """Spec scenario: Cancel inline edit — cancelling returns the original
    card and the caption is unchanged."""
    user = make_user()
    post = make_post(user, "original caption")
    client.force_login(user)

    response = client.get(f"/web/posts/{post.pk}/cancel-edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "original caption" in content
    assert 'name="caption"' not in content  # the form is closed
    post.refresh_from_db()
    assert post.caption == "original caption"


def test_cancel_inline_edit_unknown_post_id_closes_without_change(client):
    """Spec scenario: Cancel inline edit — an unknown post id (cancel or
    submit) closes the form without changing anything and without crashing."""
    user = make_user()
    post = make_post(user, "untouched caption")
    client.force_login(user)
    unknown_id = uuid.uuid4()

    cancel_response = client.get(f"/web/posts/{unknown_id}/cancel-edit/")
    submit_response = client.post(f"/web/posts/{unknown_id}/submit-edit/", {"caption": "hijacked"})
    edit_form_response = client.get(f"/web/posts/{unknown_id}/edit-form/")

    assert cancel_response.status_code == 200
    assert submit_response.status_code == 200
    assert edit_form_response.status_code == 200
    assert "hijacked" not in cancel_response.content.decode()
    assert 'name="caption"' not in submit_response.content.decode()  # form closed
    assert Post.objects.count() == 1  # nothing was created
    post.refresh_from_db()
    assert post.caption == "untouched caption"  # nothing was changed


# --- Spec scenario: Web deletion removes the card ----------------------------


def test_web_deletion_removes_the_card(client):
    """Spec scenario: Web deletion removes the card — deleting from the grid
    removes the post (media cascade with it) and shows "Post deleted!"."""
    user = make_user()
    post = make_post(user, "doomed post")
    client.force_login(user)

    response = client.post(f"/web/posts/{post.pk}/delete/")

    assert response.status_code == 200
    assert "Post deleted!" in response.content.decode()
    assert not Post.objects.filter(pk=post.pk).exists()


# --- Ownership errors surface as error toasts --------------------------------


def test_web_edit_by_non_owner_rejected(client):
    """A non-owner submitting the inline edit gets an error toast with the
    exact model error text and the caption is unchanged."""
    owner = make_user()
    intruder = make_user(username="mallory", email="mallory@example.com")
    post = make_post(owner, "owner caption")
    client.force_login(intruder)

    response = client.post(f"/web/posts/{post.pk}/submit-edit/", {"caption": "hijack"})

    assert response.status_code == 200
    assert "You can only edit your own posts" in response.content.decode()
    post.refresh_from_db()
    assert post.caption == "owner caption"


def test_web_delete_by_non_owner_rejected(client):
    """A non-owner deleting a post gets an error toast with the exact model
    error text and the post still exists."""
    owner = make_user()
    intruder = make_user(username="mallory", email="mallory@example.com")
    post = make_post(owner, "survivor post")
    client.force_login(intruder)

    response = client.post(f"/web/posts/{post.pk}/delete/")

    assert response.status_code == 200
    assert "You can only delete your own posts" in response.content.decode()
    assert Post.objects.filter(pk=post.pk).exists()


def test_web_submit_edit_rejects_over_long_caption(client):
    """A crafted POST with a caption over the limit is rejected with a field
    error toast instead of a 500 (field-format rule checked in the web layer)."""
    user = make_user()
    post = make_post(user, "short caption")
    client.force_login(user)

    response = client.post(
        f"/web/posts/{post.pk}/submit-edit/", {"caption": "x" * (CAPTION_MAX_LENGTH + 1)}
    )

    assert response.status_code == 200
    assert "no more than 2200 characters" in response.content.decode()
    post.refresh_from_db()
    assert post.caption == "short caption"
