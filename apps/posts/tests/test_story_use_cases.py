"""Use case tests for the stories capability (tasks 3.1-3.2), named after the
spec scenarios they back at the use case level."""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.posts.use_cases import (
    STORY_NOT_FOLLOWED_ERROR,
    STORY_NOT_FOUND_ERROR,
    STORY_SELF_VIEW_ERROR,
    CreateStoryInput,
    CreateStoryUseCase,
    ListFeedStoriesInput,
    ListFeedStoriesOutput,
    ListFeedStoriesUseCase,
    ViewStoryInput,
    ViewStoryUseCase,
)
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_media_root(tmp_path, settings):
    """Keep generated placeholder files inside a per-test media root."""
    settings.MEDIA_ROOT = tmp_path


def make_user(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "sup3r-secret-pw",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_follow(follower: User, following: User) -> Follow:
    return Follow.objects.create(follower=follower, following=following)


def make_story(user, **overrides):
    data = {"owner": user}
    data.update(overrides)
    return Story.objects.create(**data)


def test_create_story_success():
    """Spec scenario: Successful web creation (use case level) — the story is
    created with the generated placeholder media and its 24h expiration."""
    user = make_user()

    output = CreateStoryUseCase().execute(CreateStoryInput(owner=user))

    assert output.success is True
    assert output.error is None
    assert output.story is not None
    stored = Story.objects.get(pk=output.story.pk)
    assert stored.owner == user
    assert stored.image.name is not None and stored.image.name.endswith(".jpg")
    assert stored.expires_at == stored.created_at + timedelta(hours=24)


def test_list_feed_stories_returns_followed_groups_only():
    """Spec scenarios: Bar lists followed users with active stories + Bar
    excludes non-followed users (use case level) — only followed users'
    active stories come back, grouped per owner."""
    viewer = make_user()
    followed = make_user(username="carol", email="carol@example.com")
    stranger = make_user(username="dave", email="dave@example.com")
    make_follow(follower=viewer, following=followed)
    story = make_story(followed)
    make_story(stranger)

    output = ListFeedStoriesUseCase().execute(ListFeedStoriesInput(viewer=viewer))

    assert isinstance(output, ListFeedStoriesOutput)
    assert output.success is True
    assert [group.owner for group in output.story_groups] == [followed]
    assert [item.story for item in output.story_groups[0].stories] == [story]


def test_first_view_recorded():
    """Scenario: First view recorded (use case level) — viewing a followed
    user's active story records the view exactly once; a repeated marking is
    idempotent (spec: Repeated view is idempotent)."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    make_follow(follower=viewer, following=owner)
    story = make_story(owner)

    output = ViewStoryUseCase().execute(ViewStoryInput(story_id=story.pk, viewer=viewer))

    assert output.success is True
    assert output.error is None
    assert output.story is not None
    assert output.story.pk == story.pk
    assert StoryView.objects.filter(story=story, viewer=viewer).count() == 1

    # Repeated view: still exactly one record.
    repeat = ViewStoryUseCase().execute(ViewStoryInput(story_id=story.pk, viewer=viewer))
    assert repeat.success is True
    assert StoryView.objects.filter(story=story, viewer=viewer).count() == 1
    assert StoryService().is_viewed(story, viewer) is True


def test_self_view_rejected():
    """Scenario: Self-view rejected — viewing one's own story does not record
    a view and reports the error."""
    owner = make_user()
    story = make_story(owner)

    output = ViewStoryUseCase().execute(ViewStoryInput(story_id=story.pk, viewer=owner))

    assert output.success is False
    assert output.error == STORY_SELF_VIEW_ERROR == "You cannot view your own story"
    assert output.story is None
    assert not StoryView.objects.filter(story=story, viewer=owner).exists()


def test_non_followed_story_not_viewable():
    """Scenario: Non-followed story not viewable — the story of a user the
    viewer does not follow is rejected and never recorded."""
    owner = make_user()
    stranger = make_user(username="dave", email="dave@example.com")
    story = make_story(owner)

    output = ViewStoryUseCase().execute(ViewStoryInput(story_id=story.pk, viewer=stranger))

    assert output.success is False
    assert (
        output.error
        == STORY_NOT_FOLLOWED_ERROR
        == "You can only view stories from people you follow"
    )
    assert output.story is None
    assert not StoryView.objects.filter(story=story, viewer=stranger).exists()


def test_unknown_story_reports_not_found():
    """An unknown story identifier reports the plain not-found error."""
    output = ViewStoryUseCase().execute(ViewStoryInput(story_id=uuid.uuid4(), viewer=make_user()))

    assert output.success is False
    assert output.error == STORY_NOT_FOUND_ERROR == "Story not found"
    assert output.story is None


def test_expired_story_reports_not_found():
    """An expired story is not active anywhere in the system (spec: Story
    data model), so viewing it reports the same not-found error and records
    nothing."""
    owner = make_user()
    viewer = make_user(username="bob", email="bob@example.com")
    make_follow(follower=viewer, following=owner)
    expired = make_story(owner, expires_at=timezone.now() - timedelta(hours=1))

    output = ViewStoryUseCase().execute(ViewStoryInput(story_id=expired.pk, viewer=viewer))

    assert output.success is False
    assert output.error == STORY_NOT_FOUND_ERROR == "Story not found"
    assert not StoryView.objects.filter(story=expired, viewer=viewer).exists()
