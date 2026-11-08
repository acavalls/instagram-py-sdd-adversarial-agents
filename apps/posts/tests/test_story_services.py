from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import STORY_LIFETIME, Story, StoryView
from apps.posts.services import StoryService
from apps.social.models import Follow


def _make_user(username: str = "alice") -> User:
    return User.objects.create(username=username, email=f"{username}@example.com", password="x")


def _follow(follower: User, following: User) -> None:
    Follow.objects.create(follower=follower, following=following)


def _create_story(owner: User) -> Story:
    output = StoryService().create(owner=owner)
    assert output.success and output.story is not None
    return output.story


def _expire(story: Story) -> None:
    """Backdate a story's expiry past the cleanup boundary (bypassing save)."""
    Story.objects.filter(pk=story.pk).update(expires_at=timezone.now() - timedelta(hours=1))


def _backdate_created(story: Story, age: timedelta) -> Story:
    """Backdate a story's creation timestamp for deterministic ordering."""
    Story.objects.filter(pk=story.pk).update(created_at=timezone.now() - age)
    return Story.objects.get(pk=story.pk)


class TestCreateGeneratesPlaceholderMedia:
    @pytest.mark.django_db
    def test_create_generates_placeholder_media(self) -> None:
        owner = _make_user()

        story = _create_story(owner)

        stored = Story.objects.get(pk=story.pk)
        created_local = timezone.localtime(stored.created_at)
        assert stored.image.name.startswith(
            f"stories/{created_local:%Y}/{created_local:%m}/{created_local:%d}/"
        )
        assert stored.image.name.endswith(".jpg")
        assert stored.media_type == Story.MediaType.IMAGE
        assert stored.owner == owner
        assert stored.expires_at == stored.created_at + STORY_LIFETIME


class TestExpiredStoryIsNotActiveAnywhere:
    @pytest.mark.django_db
    def test_expired_story_is_not_active_anywhere(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        _follow(viewer, owner)
        story = _create_story(owner)
        assert story in StoryService().get_active_for_user(owner)
        assert len(StoryService().get_feed_stories(viewer)) == 1

        _expire(story)

        assert StoryService().get_active_for_user(owner) == []
        assert StoryService().get_feed_stories(viewer) == []


class TestFeedStoriesOnlyFromFollowedUsers:
    @pytest.mark.django_db
    def test_feed_stories_only_from_followed_users(self) -> None:
        viewer = _make_user("alice")
        followed = _make_user("bob")
        non_followed = _make_user("carol")
        _follow(viewer, followed)
        followed_story = _create_story(followed)
        _create_story(non_followed)
        _create_story(viewer)

        groups = StoryService().get_feed_stories(viewer)

        assert [(group.owner, [entry.story for entry in group.stories]) for group in groups] == [
            (followed, [followed_story])
        ]


class TestFeedStoriesGroupedUnviewedFirst:
    @pytest.mark.django_db
    def test_feed_stories_grouped_unviewed_first(self) -> None:
        viewer = _make_user("alice")
        viewed_owner = _make_user("bob")
        unviewed_owner = _make_user("carol")
        _follow(viewer, viewed_owner)
        _follow(viewer, unviewed_owner)
        older_viewed = _backdate_created(_create_story(viewed_owner), timedelta(hours=3))
        newest_viewed = _backdate_created(_create_story(viewed_owner), timedelta(hours=1))
        unviewed_story = _create_story(unviewed_owner)
        service = StoryService()
        for story in (older_viewed, newest_viewed):
            service.mark_viewed(story, viewer)

        groups = service.get_feed_stories(viewer)

        assert [group.owner for group in groups] == [unviewed_owner, viewed_owner]
        unviewed_group, viewed_group = groups
        assert [entry.story for entry in unviewed_group.stories] == [unviewed_story]
        assert [entry.is_viewed for entry in unviewed_group.stories] == [False]
        assert [entry.story for entry in viewed_group.stories] == [newest_viewed, older_viewed]
        assert [entry.is_viewed for entry in viewed_group.stories] == [True, True]


class TestMarkViewedIsIdempotent:
    @pytest.mark.django_db
    def test_mark_viewed_is_idempotent(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        story = _create_story(owner)
        service = StoryService()

        service.mark_viewed(story, viewer)
        service.mark_viewed(story, viewer)

        assert StoryView.objects.count() == 1
        assert StoryView.objects.get(story=story, viewer=viewer).viewer == viewer
        assert service.is_viewed(story, viewer)


class TestCleanupExpiredDeletesStoriesAndReportsCount:
    @pytest.mark.django_db
    def test_cleanup_expired_deletes_stories_and_reports_count(self) -> None:
        owner = _make_user("alice")
        viewer = _make_user("bob")
        service = StoryService()
        expired_story = _create_story(owner)
        StoryView.objects.create(story=expired_story, viewer=viewer)
        _create_story(owner)
        _expire(expired_story)
        assert Story.objects.count() == 2
        assert StoryView.objects.count() == 1

        deleted = service.cleanup_expired()

        assert deleted == 1
        assert Story.objects.count() == 1
        assert StoryView.objects.count() == 0
        assert service.cleanup_expired() == 0
