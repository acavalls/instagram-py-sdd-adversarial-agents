"""seed_demo_data management command (design decision 11, change add-social).

Creates a demo ecosystem — users, follows among them and posts with
generated placeholder media — so the followed-users feed, the suggestions
panel and the profile pages have data to explore during manual validation.

Layer discipline (config contract): everything goes through the existing
use cases/services — users through ``RegisterUserUseCase``, follows through
``FollowService`` and posts through ``CreatePostUseCase`` (the same path the
web create flow uses, so media handling is identical). The command never
touches the ORM directly.

Idempotency: when the demo users already exist the whole seed is skipped,
so re-running the command never duplicates the ecosystem.
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.accounts.use_cases import RegisterUserInput, RegisterUserUseCase
from apps.posts.use_cases import CreatePostInput, CreatePostUseCase
from apps.social.services import FollowService

# Shared password for every demo account (>= 8 characters, User rules).
DEMO_PASSWORD = "demo-password-123"

# Demo identities: (username, email). Alphanumeric usernames satisfy the
# model's username rule (no underscores allowed); the "demo" prefix avoids
# collisions with real accounts on a shared development database.
DEMO_USERS: list[tuple[str, str]] = [
    ("demoalice", "alice@example.com"),
    ("demobob", "bob@example.com"),
    ("democarol", "carol@example.com"),
    ("demodave", "dave@example.com"),
    ("demoerin", "erin@example.com"),
]

# Follows among the demo users: (follower, following) pairs, chosen so the
# feed, the suggestions panel and the profile counters all have content.
DEMO_FOLLOWS: list[tuple[str, str]] = [
    ("demoalice", "demobob"),
    ("demoalice", "democarol"),
    ("demobob", "democarol"),
    ("demobob", "demodave"),
    ("democarol", "demodave"),
    ("demodave", "demoalice"),
    ("demoerin", "demoalice"),
    ("demoerin", "demobob"),
]

# Posts created for each demo user.
POSTS_PER_USER = 3

# Fixed in-code caption pool (deterministic, same style as the web
# placeholder captions; never copyrighted assets).
DEMO_CAPTIONS: list[str] = [
    "Golden hour vibes ✨",
    "Sunday walk in the city",
    "Coffee first, everything else later",
    "New post, who dis?",
    "Late night coding session",
    "Beach day with friends",
    "Homemade pasta night 🍝",
    "Exploring the old town",
    "Sunset from the rooftop",
    "Weekend reset complete",
    "Morning run along the river",
    "Plant corner is thriving",
    "Board game night wins",
    "Fresh bread out of the oven",
    "Mountain air does wonders",
]

# Minimal valid 1x1 transparent GIF used as the generated placeholder media
# (same bytes the web create flow and the API tests use).
PLACEHOLDER_GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


class Command(BaseCommand):
    """Seed the demo ecosystem (skips when the demo users already exist)."""

    help = (
        "Create demo users, follows among them and placeholder posts so the "
        "feed, suggestions and profiles have data for manual validation."
    )

    def handle(self, *args: object, **options: object) -> None:
        """Run the seed (see module docstring for the guarantees)."""
        demo_usernames = [username for username, _email in DEMO_USERS]
        if User.objects.filter(username__in=demo_usernames).exists():
            self.stdout.write("Demo users already exist; skipping seed.")
            return

        users = self._create_users()
        self._create_follows(users)
        self._create_posts(users)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users)} demo users, {len(DEMO_FOLLOWS)} follows "
                f"and {len(users) * POSTS_PER_USER} posts."
            )
        )

    def _create_users(self) -> dict[str, User]:
        """Create every demo user through ``RegisterUserUseCase``."""
        use_case = RegisterUserUseCase()
        users: dict[str, User] = {}
        for username, email in DEMO_USERS:
            output = use_case.execute(
                RegisterUserInput(username=username, email=email, password=DEMO_PASSWORD)
            )
            if not output.success or output.user is None:
                raise CommandError(f"Could not create demo user {username}: {output.error}")
            users[username] = output.user
        return users

    def _create_follows(self, users: dict[str, User]) -> None:
        """Create the follows through ``FollowService.follow``.

        A duplicate pair is skipped (``Already following this user``) so a
        partially seeded database converges instead of crashing.
        """
        service = FollowService()
        for follower, following in DEMO_FOLLOWS:
            try:
                service.follow(users[follower], users[following])
            except ValidationError as error:
                self.stdout.write(f"Skipping follow {follower} -> {following}: {error.message}")

    def _create_posts(self, users: dict[str, User]) -> None:
        """Create the placeholder posts through ``CreatePostUseCase``.

        Captions cycle through ``DEMO_CAPTIONS`` deterministically and every
        post carries one generated placeholder GIF (same media path as the
        web create flow).
        """
        use_case = CreatePostUseCase()
        for user_index, (username, user) in enumerate(users.items()):
            for position in range(POSTS_PER_USER):
                caption_index = user_index * POSTS_PER_USER + position
                caption = DEMO_CAPTIONS[caption_index % len(DEMO_CAPTIONS)]
                output = use_case.execute(
                    CreatePostInput(
                        owner=user,
                        caption=caption,
                        media_files=[
                            SimpleUploadedFile(
                                f"placeholder-{username}-{position}.gif",
                                PLACEHOLDER_GIF_BYTES,
                                content_type="image/gif",
                            )
                        ],
                    )
                )
                if not output.success:
                    raise CommandError(f"Could not create demo post for {username}: {output.error}")
