"""Bad-attack probes for the 06-regularize-audit-drift change (web side).

Attacks: card header links to the owner profile, sidebar active state on
profile/following-modal/feed pages, and web registration regressions.
"""

import re
import uuid

import pytest
from django.core.files.base import ContentFile

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db


def _make_user(username: str) -> User:
    user = User(username=username, email=f"{username}@example.com")
    user.set_password("password-123")
    user.save()
    return user


def _login(client, user: User) -> None:
    client.force_login(user)


def _make_post(owner: User, caption: str = "caption") -> Post:
    media = (PostMediaInput(file=ContentFile(b"data", name="media-0.png"), media_type="image"),)
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(user=owner, caption=caption, media=media)
    )
    assert output.success and output.post is not None
    return output.post


def _sidebar_class_for(html: str, testid: str) -> str:
    match = re.search(rf'class="sidebar-link([^"]*)"[^>]*data-testid="{testid}"', html, re.S)
    assert match is not None, f"sidebar entry {testid} not found"
    return match.group(1)


class TestCardHeaderLinks:
    def test_bad_attack_feed_card_links_point_at_owner_profile(self, client):
        viewer = _make_user("viewer")
        owner = _make_user("cardowner")
        FollowService().follow(follower=viewer, following=owner)
        post = _make_post(owner)
        _login(client, viewer)

        html = client.get("/web/feed/").content.decode()
        expected = f'href="/web/profile/{post.owner.pk}/"'
        assert expected in html, f"feed card does not link to {expected}"
        assert "/web/users/" not in html, "stale /web/users/ link still rendered"

    def test_bad_attack_profile_grid_card_links_point_at_owner_profile(self, client):
        owner = _make_user("gridowner")
        _make_post(owner)
        _login(client, owner)

        html = client.get(f"/web/profile/{owner.pk}/").content.decode()
        expected = f'href="/web/profile/{owner.pk}/"'
        assert expected in html, f"profile grid card does not link to {expected}"

    def test_bad_attack_owner_cascade_leaves_no_orphan_card(self, client):
        viewer = _make_user("cascadeviewer")
        owner = _make_user("cascaded")
        post = _make_post(owner)
        owner_pk = owner.pk
        _login(client, viewer)

        owner.delete()

        assert not Post.objects.filter(pk=post.pk).exists()
        assert client.get(f"/web/profile/{owner_pk}/").status_code == 404


class TestSidebarActiveState:
    def test_bad_attack_profile_page_marks_profile_active_not_home(self, client):
        user = _make_user("activeself")
        _login(client, user)

        html = client.get(f"/web/profile/{user.pk}/").content.decode()
        assert "active" in _sidebar_class_for(html, "nav-profile"), (
            "Profile is not active on a profile page"
        )
        assert "active" not in _sidebar_class_for(html, "nav-home"), (
            "Home is active on a profile page"
        )

    def test_bad_attack_following_modal_page_marks_profile_active(self, client):
        user = _make_user("modalowner")
        other = _make_user("modalother")
        _login(client, other)

        html = client.get(f"/web/profile/{user.pk}/following/").content.decode()
        assert "active" in _sidebar_class_for(html, "nav-profile"), (
            "Profile not active on the following-modal page"
        )

    def test_bad_attack_feed_marks_home_active_not_profile(self, client):
        user = _make_user("feeduser")
        _login(client, user)

        html = client.get("/web/feed/").content.decode()
        assert "active" in _sidebar_class_for(html, "nav-home")
        assert "active" not in _sidebar_class_for(html, "nav-profile"), (
            "Profile active on the feed page"
        )

    def test_bad_attack_garbage_profile_paths_404_without_template_error(self, client):
        user = _make_user("garbageuser")
        _login(client, user)

        assert client.get(f"/web/profile/{uuid.uuid4()}/trailing-garbage/").status_code == 404
        assert client.get("/web/profile/not-a-uuid/").status_code == 404


class TestWebRegisterRegressions:
    def test_bad_attack_web_register_normal_username_works(self, client):
        response = client.post(
            "/web/register/",
            {
                "username": "webnormal",
                "email": "webnormal@example.com",
                "password": "password-123",
            },
        )
        assert response.status_code in (200, 302)
        assert User.objects.filter(username="webnormal").exists()

    def test_bad_attack_web_register_rejects_padded_username(self, client):
        client.post(
            "/web/register/",
            {"username": "  padded  ", "email": "padded@example.com", "password": "password-123"},
        )
        assert User.objects.filter(email="padded@example.com").count() == 0

    def test_bad_attack_web_register_email_byte_exact(self, client):
        client.post(
            "/web/register/",
            {"username": "webcase", "email": "WebCase@X.COM", "password": "password-123"},
        )
        assert User.objects.get(username="webcase").email == "WebCase@X.COM"

    def test_bad_attack_web_register_same_case_email_duplicate_rejected(self, client):
        client.post(
            "/web/register/",
            {"username": "webe1", "email": "same@x.com", "password": "password-123"},
        )
        client.post(
            "/web/register/",
            {"username": "webe2", "email": "same@x.com", "password": "password-123"},
        )
        assert not User.objects.filter(username="webe2").exists()
