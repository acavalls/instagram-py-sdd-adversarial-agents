"""Web stories tests, named after the spec scenarios they cover
(stories spec: Story creation, Stories bar on the home page, Story view
tracking, Stories bar ordering, Expired story cleanup)."""

import io
from datetime import timedelta
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

FEED_URL = "/web/feed/"
CREATE_URL = "/web/stories/create/"
UNKNOWN_STORY_URL = "/web/stories/00000000-0000-0000-0000-000000000000/view/"
RAW_PASSWORD = "sup3r-secret-pw"


def make_user(username: str = "alice", **overrides: Any) -> User:
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_placeholder_jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 40, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_story(owner: User, **overrides: Any) -> Story:
    data = {"owner": owner}
    data.update(overrides)
    story = Story(**data)
    story.image.save("story.jpg", ContentFile(make_placeholder_jpeg()), save=False)
    story.save()
    return story


def follow(follower: User, following: User) -> None:
    FollowService().follow(follower=follower, following=following)


def view_url(story: Story) -> str:
    return f"/web/stories/{story.pk}/view/"


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


# --- Spec scenario: Successful web creation ----------------------------------


def test_successful_web_creation_with_toast_and_oob_bar(client):
    """Spec scenario: Successful web creation — POST /web/stories/create/
    creates a story with a generated placeholder image and renders the
    "Story created" success toast plus the out-of-band updated stories bar."""
    user = make_user()
    client.force_login(user)

    response = client.post(CREATE_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Story created" in content
    assert 'hx-swap-oob="true"' in content  # the updated stories bar
    assert 'id="stories-bar"' in content
    assert "Your story" in content
    # The story is really stored with a generated placeholder image.
    story = Story.objects.get(owner=user)
    image_name = story.image.name
    assert image_name is not None
    assert image_name.startswith("stories/")
    assert image_name.endswith(".jpg")


def test_unauthenticated_creation_rejected(client):
    """Spec scenario: Unauthenticated creation rejected — an anonymous client
    is redirected to the login page instead of creating a story."""
    response = client.post(CREATE_URL)

    assert response.status_code == 302
    assert "/web/login/" in response.url
    assert not Story.objects.exists()


def test_create_story_rejects_get_requests(client):
    """The story creation is POST-only (a state-changing action must not be
    triggerable by GET, same convention as the web logout)."""
    user = make_user()
    client.force_login(user)

    response = client.get(CREATE_URL)

    assert response.status_code == 405
    assert not Story.objects.exists()


# --- Spec scenario: First view recorded ---------------------------------------


def test_first_view_recorded_with_toast_and_oob_bar(client):
    """Spec scenario: First view recorded — POST /web/stories/<uuid>/view/
    for a followed user's active story records the view once and renders the
    "Story viewed" success toast plus the out-of-band updated stories bar."""
    viewer = make_user()
    owner = make_user("bob")
    follow(viewer, owner)
    story = make_story(owner)
    client.force_login(viewer)

    response = client.post(view_url(story))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Story viewed" in content
    assert 'hx-swap-oob="true"' in content
    assert 'id="stories-bar"' in content
    # The view is really recorded, exactly once.
    assert StoryView.objects.filter(story=story, viewer=viewer).count() == 1


def test_view_story_rejects_get_requests(client):
    """The story view is POST-only (same convention as the story creation)."""
    viewer = make_user()
    owner = make_user("bob")
    follow(viewer, owner)
    story = make_story(owner)
    client.force_login(viewer)

    response = client.get(view_url(story))

    assert response.status_code == 405
    assert not StoryView.objects.exists()


def test_view_story_requires_login(client):
    """An anonymous visitor is redirected to the login page instead of
    viewing a story."""
    story = make_story(make_user("bob"))

    response = client.post(view_url(story))

    assert response.status_code == 302
    assert "/web/login/" in response.url
    assert not StoryView.objects.exists()


def test_view_story_unknown_story_error_toast(client):
    """Edge: an unknown (or expired) story identifier answers with the exact
    use-case error toast and the bar keeping its state — the repo convention
    for HTMX failures (a non-UUID id 404s at the route converter)."""
    viewer = make_user()
    client.force_login(viewer)

    response = client.post(UNKNOWN_STORY_URL)

    assert response.status_code == 200
    assert "Story not found" in shown_messages(response)
    assert not StoryView.objects.exists()


def test_view_story_self_view_rejected(client):
    """A user cannot record a view of their own story: the error toast flows
    from the use case and no view record is created."""
    user = make_user()
    story = make_story(user)
    client.force_login(user)

    response = client.post(view_url(story))

    assert response.status_code == 200
    assert "You cannot view your own story" in shown_messages(response)
    assert not StoryView.objects.exists()


def test_view_story_non_followed_owner_rejected(client):
    """Stories of users the viewer does not follow are not viewable: the
    error toast flows from the use case and no view record is created."""
    viewer = make_user()
    stranger = make_user("stranger")
    story = make_story(stranger)
    client.force_login(viewer)

    response = client.post(view_url(story))

    assert response.status_code == 200
    assert "You can only view stories from people you follow" in shown_messages(response)
    assert not StoryView.objects.exists()


# --- Spec scenario: Bar lists followed users with active stories --------------


def test_bar_lists_followed_users_with_active_stories(client):
    """Spec scenario: Bar lists followed users with active stories — the home
    page stories bar shows one avatar for each followed user with an active
    story, labeled with their username, above the post list."""
    user = make_user()
    followed = make_user("bob")
    follow(user, followed)
    make_story(followed)
    client.force_login(user)

    response = client.get(FEED_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="stories-bar"' in content
    assert f'hx-post="/web/stories/{Story.objects.get(owner=followed).pk}/view/"' in content
    assert "bob" in content
    # posts delta (Post listing): the stories bar renders above the post grid.
    assert content.index('id="stories-bar"') < content.index('id="post-grid"')


# --- Spec scenario: Bar excludes non-followed users ----------------------------


def test_bar_excludes_non_followed_users(client):
    """Spec scenario: Bar excludes non-followed users — a user with active
    stories who is not followed by the viewer never appears in the bar."""
    user = make_user()
    stranger = make_user("stranger")
    make_story(stranger)
    client.force_login(user)

    response = client.get(FEED_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="stories-bar"' in content
    # No avatar form for the stranger anywhere in the bar (their username
    # still appears in the suggestions panel, so assert on the avatar markup).
    assert f"/web/stories/{stranger.pk}/view/" not in content
    assert "story-avatar story-avatar-unseen" not in content
    assert "story-avatar story-avatar-viewed" not in content


# --- Spec scenario: Bar empty without followings -------------------------------


def test_bar_empty_without_followings_shows_only_add_button(client):
    """Spec scenario: Bar empty without followings — with no follows and no
    active stories of followees, the bar shows only the "Your story" add
    button (no group avatars)."""
    user = make_user()
    stranger = make_user("stranger")
    make_story(stranger)
    client.force_login(user)

    response = client.get(FEED_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Your story" in content
    # No group avatars at all (the class *usage* in markup, not the CSS rule).
    assert "story-avatar story-avatar-unseen" not in content
    assert "story-avatar story-avatar-viewed" not in content


# --- Spec scenario: Unviewed groups first -------------------------------------


def test_unviewed_groups_first_in_rendered_bar(client):
    """Spec scenario: Unviewed groups first — the unviewed followed-user
    group's avatar appears before the viewed group's avatar in the rendered
    bar (compared through each group's view URL)."""
    user = make_user()
    viewed_owner = make_user("bob")
    unviewed_owner = make_user("carol")
    follow(user, viewed_owner)
    follow(user, unviewed_owner)
    viewed_story = make_story(viewed_owner)
    unviewed_story = make_story(unviewed_owner)
    StoryView.objects.create(story=viewed_story, viewer=user)
    client.force_login(user)

    response = client.get(FEED_URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert content.index(f"/web/stories/{unviewed_story.pk}/view/") < content.index(
        f"/web/stories/{viewed_story.pk}/view/"
    )


# --- Spec scenario: Ring updates after viewing ---------------------------------


def test_ring_updates_to_viewed_after_viewing(client):
    """Spec scenario: Ring updates after viewing — before the view the
    group's avatar carries the unseen ring state; after marking the newest
    story viewed, the OOB bar re-render shows the viewed ring state."""
    user = make_user()
    owner = make_user("bob")
    follow(user, owner)
    story = make_story(owner)
    client.force_login(user)

    before = client.get(FEED_URL)
    assert "story-avatar story-avatar-unseen" in before.content.decode()

    response = client.post(view_url(story))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Story viewed" in content
    # The OOB bar re-render shows the group with the viewed ring state.
    assert "story-avatar story-avatar-viewed" in content
    assert "story-avatar story-avatar-unseen" not in content
    assert f'hx-post="/web/stories/{story.pk}/view/"' in content


# --- Spec scenario: Lazy purge on home render ----------------------------------


def test_expired_stories_purged_on_home_render(client):
    """Spec scenario: Lazy purge on home render — rendering the home page
    deletes the expired stories (and their view records) before rendering, so
    they never appear in the stories bar."""
    user = make_user()
    owner = make_user("bob")
    follow(user, owner)
    expired_story = make_story(owner, expires_at=timezone.now() - timedelta(hours=1))
    StoryView.objects.create(story=expired_story, viewer=user)
    client.force_login(user)

    response = client.get(FEED_URL)

    assert response.status_code == 200
    # The expired story and its view record are gone.
    assert not Story.objects.filter(pk=expired_story.pk).exists()
    assert not StoryView.objects.filter(story=expired_story).exists()
    # And it never made it into the bar.
    assert f"/web/stories/{expired_story.pk}/view/" not in response.content.decode()


def test_active_story_survives_home_render(client):
    """The lazy purge only removes expired stories: an active story of a
    followed user stays stored and keeps its view record after a home
    render."""
    user = make_user()
    owner = make_user("bob")
    follow(user, owner)
    story = make_story(owner, expires_at=timezone.now() + timedelta(hours=1))
    view = StoryView.objects.create(story=story, viewer=user)
    client.force_login(user)

    client.get(FEED_URL)

    assert Story.objects.filter(pk=story.pk).exists()
    assert StoryView.objects.filter(pk=view.pk).exists()
