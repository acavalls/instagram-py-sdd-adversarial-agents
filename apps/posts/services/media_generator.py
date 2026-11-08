"""Deterministic placeholder media for web-created posts.

The web UI has no file picker (fixed stack decision): post creation from
the web generates a placeholder image with Pillow and picks a random
preset caption. The image is deterministic given its seed (same seed,
same bytes) and rendered from a fixed in-app palette, honoring the
"deterministic media" principle (never copyrighted assets).
"""

import hashlib
import io
import random
from typing import Final

from django.core.files.base import ContentFile
from PIL import Image

CAPTIONS: Final[list[str]] = [
    "Golden hour vibes",
    "Weekend wanderings",
    "Coffee and city lights",
    "Somewhere between here and there",
    "Little moments, big memories",
    "Chasing sunsets",
    "New day, new frame",
    "Back to basics",
    "Colors of the season",
    "One more from the archive",
]

IMAGE_SIZE: Final[int] = 1080

PALETTE: Final[tuple[tuple[int, int, int], ...]] = (
    (64, 93, 230),
    (221, 94, 137),
    (255, 154, 60),
    (72, 187, 120),
    (160, 90, 220),
    (240, 200, 80),
    (80, 170, 220),
    (220, 120, 90),
)


def random_caption() -> str:
    """A random preset caption from the app's caption list."""
    return random.choice(CAPTIONS)  # noqa: S311


def _palette_color(seed: str) -> tuple[int, int, int]:
    """The palette color the seed deterministically selects."""
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return PALETTE[int(digest, 16) % len(PALETTE)]


def generate_placeholder_image(seed: str, name: str = "placeholder.png") -> ContentFile:
    """A deterministic placeholder image file for the given seed.

    The seed selects a palette color through a stable hash, so the same
    seed always produces the same image bytes.
    """
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), _palette_color(seed))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=name)


def generate_placeholder_story_image(seed: str, name: str = "placeholder.jpg") -> ContentFile:
    """A deterministic placeholder JPEG for a story with the given seed.

    Same palette/hash convention as the post placeholder, saved as JPEG
    for the story media type.
    """
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), _palette_color(seed))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name=name)
