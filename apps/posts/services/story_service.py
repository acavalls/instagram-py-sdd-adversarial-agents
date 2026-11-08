import uuid
from dataclasses import dataclass

from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services.media_generator import generate_placeholder_story_image
from apps.social.models import Follow
from apps.social.services.follow_service import FollowService


@dataclass(frozen=True, slots=True)
class StoryOutput:
    """Result of creating a story."""

    success: bool
    story: Story | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class StoryFeedEntry:
    """One story in a feed group with the viewer's seen state."""

    story: Story
    is_viewed: bool


@dataclass(frozen=True, slots=True)
class StoryFeedGroup:
    """One owner's active stories (newest first) for the stories bar."""

    owner: User
    stories: list[StoryFeedEntry]


class StoryService:
    """Domain service for story persistence, view tracking and cleanup."""

    def __init__(self, follow_service: FollowService | None = None) -> None:
        self._follow_service = follow_service or FollowService()

    def create(self, *, owner: User) -> StoryOutput:
        """Create a story for the owner with a generated placeholder image."""
        story = Story(owner=owner)
        placeholder = generate_placeholder_story_image(seed=str(uuid.uuid4()))
        story.image.save(placeholder.name or "placeholder.jpg", placeholder, save=False)
        story.save()
        return StoryOutput(success=True, story=story)

    def get_active_by_id(self, story_id: object) -> Story | None:
        """Fetch an active story by identifier with its owner loaded."""
        return Story.objects.select_related("owner").filter(pk=story_id).active().first()

    def get_active_for_user(self, owner: User) -> list[Story]:
        """The owner's own active stories, newest first."""
        return list(Story.objects.filter(owner=owner).active())

    def get_feed_stories(self, viewer: User) -> list[StoryFeedGroup]:
        """Active stories of the users `viewer` follows, grouped per owner.

        Each story carries the viewer's seen state; groups whose latest
        story is unviewed come first, then viewed groups, and within each
        group the stories keep their newest-first creation order.
        """
        followee_ids = Follow.objects.filter(follower=viewer).values_list("following_id", flat=True)
        stories = list(
            Story.objects.filter(owner_id__in=followee_ids).select_related("owner").active()
        )
        viewed_story_ids = set(
            StoryView.objects.filter(
                viewer=viewer, story_id__in=[story.pk for story in stories]
            ).values_list("story_id", flat=True)
        )
        entries_by_owner: dict[uuid.UUID, list[StoryFeedEntry]] = {}
        for story in stories:
            entry = StoryFeedEntry(story=story, is_viewed=story.pk in viewed_story_ids)
            entries_by_owner.setdefault(story.owner_id, []).append(entry)
        groups = [
            StoryFeedGroup(owner=entries[0].story.owner, stories=entries)
            for entries in entries_by_owner.values()
        ]
        groups.sort(
            key=lambda group: (
                group.stories[0].is_viewed,
                -group.stories[0].story.created_at.timestamp(),
                group.owner.username,
            )
        )
        return groups

    def mark_viewed(self, story: Story, viewer: User) -> StoryView:
        """Record the (story, viewer) view once (repeat calls are no-ops)."""
        view, _ = StoryView.objects.get_or_create(story=story, viewer=viewer)
        return view

    def is_viewed(self, story: Story, viewer: User) -> bool:
        """Whether `viewer` has already viewed the story."""
        return StoryView.objects.filter(story=story, viewer=viewer).exists()

    def cleanup_expired(self) -> int:
        """Delete expired stories (their view records go with them)."""
        expired = Story.objects.filter(expires_at__lte=timezone.now())
        count = expired.count()
        expired.delete()
        return count
