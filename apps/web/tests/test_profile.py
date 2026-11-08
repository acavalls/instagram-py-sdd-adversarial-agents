import re
import uuid

import pytest

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import PostService
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"
PROFILE_PAGE_SIZE = 12


def _register_and_login(client, username: str = "alice") -> User:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})
    return User.objects.get(username=username)


def _create_post(user: User, caption: str = "hello") -> Post:
    output = CreatePostUseCase(post_service=PostService()).execute(
        CreatePostInput(user=user, caption=caption)
    )
    assert output.success and output.post is not None
    return output.post


def _profile_url(user: User) -> str:
    return f"/web/profile/{user.pk}/"


@pytest.mark.django_db
class TestOwnProfile:
    def test_own_profile_shows_stats_and_editable_grid(self, client) -> None:
        user = _register_and_login(client)
        _create_post(user, caption="first post")
        _create_post(user, caption="second post")

        response = client.get(_profile_url(user))

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="profile-stat-posts"' in html
        assert ">2</span>" in html
        assert 'data-testid="post-edit-button"' in html
        assert 'data-testid="post-delete-button"' in html
        assert 'data-testid="follow-button"' not in html


@pytest.mark.django_db
class TestOtherUserProfile:
    def test_other_user_profile_shows_stats_and_follow_state(self, client) -> None:
        owner = _register_and_login(client, "bob")
        _create_post(owner, caption="bob post")
        visitor = _register_and_login(client, "alice")

        response = client.get(_profile_url(owner))
        html = response.content.decode()

        assert response.status_code == 200
        assert 'data-testid="follow-button"' in html
        assert 'data-following="false"' in html
        assert re.search(r">\s*Follow\s*</button>", html)
        assert 'data-testid="post-edit-button"' not in html
        assert 'data-testid="post-delete-button"' not in html

        FollowService().follow(follower=visitor, following=owner)
        response = client.get(_profile_url(owner))
        html = response.content.decode()

        assert 'data-following="true"' in html
        assert re.search(r">\s*Following\s*</button>", html)


@pytest.mark.django_db
class TestUnknownProfile:
    def test_unknown_profile_responds_404(self, client) -> None:
        _register_and_login(client)

        response = client.get(f"/web/profile/{uuid.uuid4()}/")

        assert response.status_code == 404


@pytest.mark.django_db
class TestSidebarProfileLink:
    def test_profile_link_points_to_own_profile(self, client) -> None:
        user = _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        match = _anchor_tag(html, "nav-profile")
        assert f'href="{_profile_url(user)}"' in match


def _anchor_tag(html: str, testid: str) -> str:
    match = re.search(rf"<a [^>]*data-testid=\"{testid}\"[^>]*>", html)
    assert match, f"anchor {testid} not found"
    return match.group(0)


@pytest.mark.django_db
class TestProfileGridPagination:
    def test_profile_grid_loads_more_posts_on_scroll(self, client) -> None:
        user = _register_and_login(client)
        for number in range(1, 14):
            _create_post(user, caption=f"caption {number:02d}")

        full_page = client.get(_profile_url(user)).content.decode()
        assert full_page.count('data-testid="post-card"') == PROFILE_PAGE_SIZE
        assert "caption 13" in full_page
        assert "caption 01" not in full_page
        assert 'data-testid="profile-sentinel"' in full_page

        htmx_response = client.get(f"{_profile_url(user)}?page=2", headers={"HX-Request": "true"})
        htmx_html = htmx_response.content.decode()

        assert htmx_response.status_code == 200
        assert "<aside" not in htmx_html
        assert 'data-testid="post-card"' in htmx_html
        assert "caption 01" in htmx_html
        assert "caption 12" not in htmx_html
        assert 'data-testid="profile-sentinel"' not in htmx_html
        assert 'data-testid="profile-end"' in htmx_html

        plain_response = client.get(f"{_profile_url(user)}?page=2")
        plain_html = plain_response.content.decode()

        assert plain_response.status_code == 200
        assert "<aside" in plain_html
        assert "caption 01" in plain_html
        assert 'data-testid="profile-end"' in plain_html


@pytest.mark.django_db
class TestProfileEmptyGrid:
    def test_profile_grid_without_posts_shows_an_empty_message(self, client) -> None:
        user = _register_and_login(client)

        response = client.get(_profile_url(user))

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="profile-empty"' in html
        assert "No posts yet." in html
        assert 'data-testid="profile-grid-item"' not in html


@pytest.mark.django_db
class TestProfileHeader:
    def test_profile_header_shows_avatar_stats_and_tabs(self, client) -> None:
        user = _register_and_login(client, "carol")
        _create_post(user, caption="carol post")

        response = client.get(_profile_url(user))

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-testid="profile-avatar"' in html
        assert ">C</div>" in html
        assert 'data-testid="profile-username"' in html
        assert "carol" in html
        assert 'data-testid="profile-stat-posts"' in html
        assert 'data-testid="profile-stat-followers"' in html
        assert 'data-testid="profile-stat-following"' in html
        assert 'data-testid="profile-tabs"' in html
        assert 'data-testid="profile-tab-posts"' in html
        assert 'aria-current="page"' in html
        saved_tag = _anchor_tag(html, "profile-tab-saved")
        tagged_tag = _anchor_tag(html, "profile-tab-tagged")
        assert "href" not in saved_tag
        assert "href" not in tagged_tag
        assert "SAVED" in html
        assert "TAGGED" in html

    def test_following_stat_opens_the_modal(self, client) -> None:
        user = _register_and_login(client)

        html = client.get(_profile_url(user)).content.decode()

        match = _anchor_tag(html, "profile-stat-following-link")
        assert f'href="{_profile_url(user)}following/"' in match


@pytest.mark.django_db
class TestProfileGridOverlay:
    def test_grid_item_shows_overlay(self, client) -> None:
        user = _register_and_login(client)
        _create_post(user, caption="overlay post")
        _create_post(user, caption="overlay post two")

        html = client.get(_profile_url(user)).content.decode()

        assert html.count('data-testid="profile-grid-item"') == 2
        assert html.count('data-testid="grid-item-overlay"') == 2
        assert 'data-testid="post-media"' in html


@pytest.mark.django_db
class TestNonHtmxProfileWindow:
    def test_non_htmx_profile_request_with_a_page_parameter_renders_the_full_page(
        self, client
    ) -> None:
        user = _register_and_login(client)
        for number in range(1, 14):
            _create_post(user, caption=f"caption {number:02d}")

        response = client.get(f"{_profile_url(user)}?page=2")

        assert response.status_code == 200
        html = response.content.decode()
        assert "<aside" in html
        assert 'data-testid="sidebar"' in html
        assert "caption 01" in html
        assert "caption 12" not in html
        assert "caption 13" not in html
        assert 'data-testid="profile-end"' in html


@pytest.mark.django_db
class TestProfileGridCardAnatomy:
    def test_grid_item_shows_the_post_card_anatomy(self, client) -> None:
        user = _register_and_login(client)
        _create_post(user, caption="anatomy post")

        html = client.get(_profile_url(user)).content.decode()
        start = html.index('data-testid="profile-grid-item"')
        end = html.index('data-testid="profile-end"')
        item = html[start:end]

        assert 'data-testid="post-card"' in item
        assert 'data-testid="post-avatar"' in item
        assert 'data-testid="post-username"' in item
        assert f'href="{_profile_url(user)}"' in item
        assert "anatomy post" in item
        assert 'data-testid="post-actions"' in item
        assert 'data-testid="post-media"' in item
        assert 'data-testid="post-edit-button"' in item
        assert 'data-testid="post-delete-button"' in item


@pytest.mark.django_db
class TestWebEditCaptionLimit:
    def test_web_edit_caption_above_limit_keeps_post_unchanged_and_reports_error(
        self, client
    ) -> None:
        user = _register_and_login(client)
        post = _create_post(user, caption="original caption")
        oversized_caption = "a" * 2201

        response = client.post(
            f"/web/posts/{post.pk}/edit/",
            {"caption": oversized_caption},
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
        html = response.content.decode()
        assert "Caption cannot exceed 2200 characters" in html
        assert 'data-testid="post-edit-form"' in html
        post.refresh_from_db()
        assert post.caption == "original caption"
