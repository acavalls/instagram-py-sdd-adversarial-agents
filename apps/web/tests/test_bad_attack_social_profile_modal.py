"""Bad attack (GBU): profile, following modal and cross-capability edges.

Attacks the "User profile page" and "Following list" requirements plus the
cross-capability guarantees: zero counters, hostile modal search queries,
a 100+ follows modal, cross-user/anonymous access, non-HTMX POSTs on the
toggle endpoints, CSRF enforcement, and the posts API staying own-posts-only.
"""

import uuid

import pytest
from django.core.files.base import ContentFile
from django.test import Client

from apps.accounts.models import User
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

REGISTER_URL = "/web/register/"
LOGIN_URL = "/web/login/"


def _register_and_login(client: Client, username: str) -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _login(client: Client, username: str) -> User:
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _create_post(user: User, caption: str = "hello") -> None:
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(
            user=user,
            caption=caption,
            media=(PostMediaInput(file=ContentFile(b"data", name="m.png"), media_type="image"),),
        )
    )
    assert output.success and output.post is not None


class TestBadAttackProfileZeroCounters:
    def test_bad_attack_profile_of_user_with_zero_everything(self, client: Client) -> None:
        _register_and_login(client, "zeroviewer")
        ghost = _register_and_login(client, "zeroghost")
        _login(client, "zeroviewer")

        response = client.get(f"/web/profile/{ghost.pk}/")
        html = response.content.decode()

        assert response.status_code == 200
        assert 'data-testid="profile-stat-posts">0<' in html
        assert 'data-testid="profile-stat-followers">0<' in html
        assert 'data-testid="profile-stat-following">0<' in html
        assert "No posts yet." in html
        assert 'data-following="false"' in html

    def test_bad_attack_unknown_profile_still_404(self, client: Client) -> None:
        _register_and_login(client, "unknownvisitor")
        response = client.get(f"/web/profile/{uuid.uuid4()}/")
        assert response.status_code == 404


class TestBadAttackFollowingModalSearch:
    @pytest.fixture()
    def modal_setup(self, client: Client) -> tuple[User, User]:
        owner = _register_and_login(client, "modalowner")
        friends = [_register_and_login(client, f"modalfriend{i}") for i in range(3)]
        _login(client, "modalowner")
        for friend in friends:
            FollowService().follow(follower=owner, following=friend)
        return owner, friends[0]

    @pytest.mark.parametrize(
        "query",
        ["%", "_", "\\", "'", '"', ";", "/*", "üņïçø", "a" * 10000, "modalfriend"],
    )
    def test_bad_attack_modal_search_hostile_queries(
        self, client: Client, modal_setup: tuple[User, User], query: str
    ) -> None:
        owner, friend = modal_setup
        response = client.get(f"/web/profile/{owner.pk}/following/", {"q": query})
        html = response.content.decode()

        assert response.status_code == 200
        if query == "modalfriend":
            assert "modalfriend0" in html
        else:
            assert "modalfriend0" not in html or query == "a" * 10000

    def test_bad_attack_modal_q_wildcards_are_literal(self, client: Client) -> None:
        owner = _register_and_login(client, "wildowner")
        _register_and_login(client, "wildx")
        _login(client, "wildowner")
        target = User.objects.get(username="wildx")
        FollowService().follow(follower=owner, following=target)

        for query in ("%", "_", "100%"):
            response = client.get(f"/web/profile/{owner.pk}/following/", {"q": query})
            html = response.content.decode()
            assert response.status_code == 200
            assert 'data-testid="following-empty"' in html, f"{query!r} acted as a wildcard"


class TestBadAttackFollowingModalLargeAndAccess:
    def test_bad_attack_modal_with_120_follows(self, client: Client) -> None:
        owner = _register_and_login(client, "bulkowner")
        followed = []
        for index in range(120):
            followed.append(_register_and_login(client, f"bulkf{index:03d}"))
        _login(client, "bulkowner")
        for target in followed:
            FollowService().follow(follower=owner, following=target)

        response = client.get(f"/web/profile/{owner.pk}/following/")
        html = response.content.decode()
        assert response.status_code == 200
        assert html.count('data-testid="following-row"') == 120

        partial = client.get(f"/web/profile/{owner.pk}/following/", headers={"HX-Request": "true"})
        assert partial.status_code == 200
        assert "<html" not in partial.content.decode()[:200].lower()
        assert partial.content.decode().count('data-testid="following-row"') == 120

    def test_bad_attack_modal_public_to_logged_in_users_but_not_anonymous(
        self, client: Client
    ) -> None:
        owner = _register_and_login(client, "accessowner")
        _register_and_login(client, "accessstranger")
        _login(client, "accessstranger")

        response = client.get(f"/web/profile/{owner.pk}/following/")
        assert response.status_code == 200

        anonymous = Client()
        response = anonymous.get(f"/web/profile/{owner.pk}/following/")
        assert response.status_code == 302
        assert "/web/login/" in response["Location"]


class TestBadAttackFollowEndpointHardening:
    def test_bad_attack_non_htmx_post_still_works(self, client: Client) -> None:
        alice = _register_and_login(client, "plainalice")
        bob = _register_and_login(client, "plainbob")
        _login(client, "plainalice")

        response = client.post(f"/web/profile/{bob.pk}/follow/")

        assert response.status_code == 200
        assert FollowService().is_following(alice, bob)
        response = client.post(f"/web/profile/{bob.pk}/unfollow/")
        assert response.status_code == 200
        assert not FollowService().is_following(alice, bob)

    def test_bad_attack_csrf_enforced_on_follow(self, client: Client) -> None:
        alice = _register_and_login(client, "csrfalice")
        bob = _register_and_login(client, "csrfbob")
        enforcing = Client(enforce_csrf_checks=True)
        login_page = enforcing.get(LOGIN_URL)
        token = login_page.cookies["csrftoken"].value

        response = enforcing.post(
            LOGIN_URL,
            {"username": "csrfalice", "password": "password123", "csrfmiddlewaretoken": token},
        )

        assert response.status_code == 302, "attack prelude failed: login rejected"

        # POST without any CSRF token must be refused by the middleware.
        response = enforcing.post(f"/web/profile/{bob.pk}/follow/")

        assert response.status_code == 403
        assert not FollowService().is_following(alice, bob)

    def test_bad_attack_anonymous_cannot_toggle_follow(self, client: Client) -> None:
        bob = _register_and_login(client, "anonbob")
        anonymous = Client()
        for suffix in ("follow/", "unfollow/"):
            response = anonymous.post(f"/web/profile/{bob.pk}/{suffix}")
            assert response.status_code == 302
            assert "/web/login/" in response["Location"]


class TestBadAttackPostsApiUnchanged:
    def test_bad_attack_api_posts_does_not_leak_followed_users_posts(self, client: Client) -> None:
        alice = _register_and_login(client, "apialice")
        bob = _register_and_login(client, "apibob")
        _create_post(alice, "alice-own")
        _create_post(bob, "bob-secret")
        FollowService().follow(follower=alice, following=bob)

        client.force_login(alice)
        response = client.get("/api/posts/")
        body = response.content.decode()

        assert response.status_code == 200
        assert "alice-own" in body
        assert "bob-secret" not in body
