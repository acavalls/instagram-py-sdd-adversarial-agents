import pytest

LOGIN_URL = "/web/login/"
FEED_URL = "/web/feed/"
REGISTER_URL = "/web/register/"


def _register_and_login(client, username: str = "alice") -> None:
    client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    client.post(LOGIN_URL, {"username": username, "password": "password123"})


@pytest.mark.django_db
class TestFeedView:
    def test_placeholder_requires_login(self, client) -> None:
        response = client.get(FEED_URL)

        assert response.status_code == 302
        assert response["Location"].startswith(LOGIN_URL)

    def test_logged_in_user_reaches_the_placeholder(self, client) -> None:
        _register_and_login(client)

        response = client.get(FEED_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-placeholder="feed-empty"' in html
        assert "Your feed is empty" in html
