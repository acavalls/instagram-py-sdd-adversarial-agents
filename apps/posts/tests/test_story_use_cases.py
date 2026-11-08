import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.posts.use_cases import (
    ERROR_NOT_FOLLOWING_OWNER,
    ERROR_SELF_VIEW,
    ERROR_STORY_NOT_FOUND,
    CreateStoryInput,
    CreateStoryUseCase,
    ListFeedStoriesInput,
    ListFeedStoriesOutput,
    ListFeedStoriesUseCase,
    ViewStoryInput,
    ViewStoryUseCase,
)
from apps.social.models import Follow
from apps.social.services.follow_service import FollowService


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _follow(follower: User, following: User) -> None:
    Follow.objects.create(follower=follower, following=following)


def _create_story(owner: User) -> Story:
    output = StoryService().create(owner=owner)
    assert output.success and output.story is not None
    return output.story


def _expire(story: Story) -> None:
    Story.objects.filter(pk=story.pk).update(expires_at=timezone.now() - timedelta(hours=1))


def _view(story_id: uuid.UUID, viewer: User):
    return ViewStoryUseCase(StoryService(), FollowService()).execute(
        ViewStoryInput(story_id=story_id, viewer=viewer)
    )


class TestCreateStoryUseCase:
    @pytest.mark.django_db
    def test_successful_creation_with_placeholder_media(self) -> None:
        user = _make_user()

        output = CreateStoryUseCase(StoryService()).execute(CreateStoryInput(user=user))

        assert output.success and output.error is None
        assert output.story is not None
        assert output.story.owner == user
        assert output.story.image.name is not None
        assert output.story.image.name.startswith("stories/")

    @pytest.mark.django_db
    def test_successful_listing_returns_followed_groups(self) -> None:
        viewer = _make_user("alice")
        followed = _make_user("bob")
        _follow(viewer, followed)
        story = _create_story(followed)

        output = ListFeedStoriesUseCase(StoryService()).execute(ListFeedStoriesInput(user=viewer))

        assert isinstance(output, ListFeedStoriesOutput)
        assert output.success and output.error is None
        assert [group.owner for group in output.groups] == [followed]
        assert [entry.story for entry in output.groups[0].stories] == [story]


class TestSelfViewRejected:
    @pytest.mark.django_db
    def test_self_view_rejected(self) -> None:
        owner = _make_user("alice")
        story = _create_story(owner)

        output = _view(story.pk, owner)

        assert not output.success
        assert output.error == ERROR_SELF_VIEW
        assert output.error == "You cannot view your own story"
        assert StoryView.objects.count() == 0


class TestNonFollowedStoryNotViewable:
    @pytest.mark.django_db
    def test_non_followed_story_not_viewable(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        story = _create_story(owner)

        output = _view(story.pk, viewer)

        assert not output.success
        assert output.error == ERROR_NOT_FOLLOWING_OWNER
        assert output.error == "You can only view stories from people you follow"
        assert StoryView.objects.count() == 0


class TestUnknownOrExpiredStoryRejected:
    @pytest.mark.django_db
    def test_unknown_story_rejected(self) -> None:
        viewer = _make_user("bob")

        output = _view(uuid.uuid4(), viewer)

        assert not output.success
        assert output.error == ERROR_STORY_NOT_FOUND
        assert output.error == "Story not found"
        assert StoryView.objects.count() == 0

    @pytest.mark.django_db
    def test_expired_story_rejected(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        _follow(viewer, owner)
        story = _create_story(owner)
        _expire(story)

        output = _view(story.pk, viewer)

        assert not output.success
        assert output.error == ERROR_STORY_NOT_FOUND
        assert StoryView.objects.count() == 0


class TestFirstViewRecorded:
    @pytest.mark.django_db
    def test_first_view_recorded(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        _follow(viewer, owner)
        story = _create_story(owner)

        output = _view(story.pk, viewer)

        assert output.success and output.error is None
        assert output.story == story
        assert StoryView.objects.get(story=story, viewer=viewer).viewer == viewer
        assert StoryService().is_viewed(story, viewer)


class TestRepeatedViewIsIdempotent:
    @pytest.mark.django_db
    def test_repeated_view_is_idempotent(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        _follow(viewer, owner)
        story = _create_story(owner)

        first = _view(story.pk, viewer)
        second = _view(story.pk, viewer)

        assert first.success and second.success
        assert StoryView.objects.count() == 1
