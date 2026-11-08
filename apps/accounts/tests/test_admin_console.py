import pytest
from django.contrib.auth.hashers import check_password

from apps.accounts.models import User
from apps.posts.models import Post, Story
from apps.social.models import Follow

ADMIN_INDEX_URL = "/admin/"
ADMIN_LOGIN_URL = "/admin/login/"
USER_CHANGE_PASSWORD_URL = "/admin/accounts/user/{pk}/password/"

CHANGELIST_URLS = {
    User: "/admin/accounts/user/",
    Post: "/admin/posts/post/",
    Story: "/admin/posts/story/",
    Follow: "/admin/social/follow/",
}


def _create_user(username: str = "alice", email: str = "alice@example.com", **extra):
    return User.objects.create(username=username, email=email, password="password123", **extra)


@pytest.fixture
def staff_user() -> User:
    return _create_user(
        username="staffer",
        email="staffer@example.com",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def staff_client(client, staff_user: User):
    client.force_login(staff_user)
    return client


def _searched_queryset(client, changelist_url: str, query: str) -> set:
    response = client.get(changelist_url, {"q": query})
    assert response.status_code == 200
    assert b'name="q"' in response.content
    return set(response.context["cl"].queryset)


@pytest.mark.django_db
class TestAdminConsole:
    def test_anonymous_visitor_redirected_to_admin_login(self, client) -> None:
        response = client.get(ADMIN_INDEX_URL)

        assert response.status_code == 302
        assert response.headers["Location"].startswith(ADMIN_LOGIN_URL)

        login_page = client.get(ADMIN_LOGIN_URL)
        assert login_page.status_code == 200
        assert b'name="username"' in login_page.content
        assert b'name="password"' in login_page.content

    def test_non_staff_user_redirected_to_admin_login(self, client) -> None:
        user = _create_user()
        client.force_login(user)

        response = client.get(ADMIN_INDEX_URL)

        assert response.status_code == 302
        assert response.headers["Location"].startswith(ADMIN_LOGIN_URL)

    def test_staff_manages_domain_models(self, staff_client, staff_user: User) -> None:
        post = Post.objects.create(owner=staff_user, caption="hello")
        story = Story.objects.create(owner=staff_user, image="")
        follow = Follow.objects.create(follower=staff_user, following=_create_user(username="bob"))

        index = staff_client.get(ADMIN_INDEX_URL)
        assert index.status_code == 200
        listed = {
            (app["app_label"], model["object_name"])
            for app in index.context_data["available_apps"]
            for model in app["models"]
        }
        expected = {
            ("accounts", "User"),
            ("posts", "Post"),
            ("posts", "Story"),
            ("social", "Follow"),
        }
        assert expected <= listed

        change_urls = {
            User: f"/admin/accounts/user/{staff_user.pk}/change/",
            Post: f"/admin/posts/post/{post.pk}/change/",
            Story: f"/admin/posts/story/{story.pk}/change/",
            Follow: f"/admin/social/follow/{follow.pk}/change/",
        }
        for model, changelist_url in CHANGELIST_URLS.items():
            changelist = staff_client.get(changelist_url)
            assert changelist.status_code == 200
            change_view = staff_client.get(change_urls[model])
            assert change_view.status_code == 200

        other_user = _create_user(username="carol", email="carol@example.com")
        other_post = Post.objects.create(owner=other_user, caption="unrelated caption")
        other_story = Story.objects.create(owner=other_user, image="")
        other_follow = Follow.objects.create(follower=other_user, following=staff_user)

        user_results = _searched_queryset(staff_client, CHANGELIST_URLS[User], "staffer")
        assert staff_user in user_results
        assert other_user not in user_results

        post_results = _searched_queryset(staff_client, CHANGELIST_URLS[Post], "hello")
        assert post in post_results
        assert other_post not in post_results

        story_results = _searched_queryset(staff_client, CHANGELIST_URLS[Story], "staffer")
        assert story in story_results
        assert other_story not in story_results

        follow_results = _searched_queryset(staff_client, CHANGELIST_URLS[Follow], "bob")
        assert follow in follow_results
        assert other_follow not in follow_results

    def test_admin_set_passwords_are_hashed(self, staff_client, staff_user: User) -> None:
        target = _create_user(username="bob", email="bob@example.com")
        url = USER_CHANGE_PASSWORD_URL.format(pk=target.pk)
        new_password = "brand-new-secret"

        response = staff_client.post(url, {"password1": new_password, "password2": new_password})

        assert response.status_code == 302
        target.refresh_from_db()
        assert target.password != new_password
        assert check_password(new_password, target.password)
