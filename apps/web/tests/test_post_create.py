import pytest

from apps.posts.models import Post
from apps.posts.services.media_generator import CAPTIONS

LOGIN_URL = "/web/login/"
REGISTER_URL = "/web/register/"
FEED_URL = "/web/feed/"
CREATE_URL = "/web/posts/create/"


def _register_and_login(client, username: str = "alice") -> None:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})


@pytest.mark.django_db
class TestCreatePostView:
    def test_successful_web_creation(self, client) -> None:
        _register_and_login(client)

        response = client.post(CREATE_URL, follow=True)

        assert response.status_code == 200
        assert response.request["PATH_INFO"] == FEED_URL
        html = response.content.decode()
        assert "Post created!" in html
        post = Post.objects.get(owner__username="alice")
        assert post.caption in CAPTIONS
        media = post.media.all()
        assert media.count() == 1
        first_media = media.first()
        assert first_media is not None
        assert first_media.media_type == "image"
        assert "post_media/" in first_media.file.name

    def test_create_submits_the_post_creation_form(self, client) -> None:
        _register_and_login(client)

        html = client.get(FEED_URL).content.decode()

        assert 'method="post"' in html
        assert 'action="/web/posts/create/"' in html
        assert 'data-testid="nav-create"' in html
        assert html.index('action="/web/posts/create/"') < html.index('data-testid="nav-create"')

    def test_create_requires_login(self, client) -> None:
        response = client.post(CREATE_URL)

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)
