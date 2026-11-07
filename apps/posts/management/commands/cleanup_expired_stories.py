"""cleanup_expired_stories management command (design decision 6, change
add-stories).

Purges the expired stories on demand — the explicit counterpart of the lazy
cleanup the home render performs — reporting how many stories were deleted.
``StoryView`` records cascade with their story via the FK
``on_delete=CASCADE`` (spec: Expired story cleanup).

Layer discipline (config contract): the deletion logic lives in
``StoryService.cleanup_expired`` (the same path the web feed uses); the
command only orchestrates the call and reports the count, never touching the
ORM directly.
"""

from django.core.management.base import BaseCommand

from apps.posts.services import StoryService


class Command(BaseCommand):
    """Delete every expired story and report the number removed."""

    help = (
        "Delete the expired stories (and their view records, which cascade) "
        "and report how many stories were removed."
    )

    def handle(self, *args: object, **options: object) -> None:
        """Run the cleanup and print the deleted count."""
        deleted = StoryService().cleanup_expired()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired stories."))
