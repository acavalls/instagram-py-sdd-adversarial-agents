from django.core.management.base import BaseCommand

from apps.posts.services import StoryService


class Command(BaseCommand):
    """Purge expired stories (and their view records) on demand."""

    help = (
        "Delete expired stories together with their view records and report "
        "how many stories were deleted."
    )

    def handle(self, *args: object, **options: object) -> None:
        deleted = StoryService().cleanup_expired()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired stories."))
