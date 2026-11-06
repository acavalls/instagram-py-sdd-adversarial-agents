"""Settings for the test suite (pytest-django)."""

from .base import *  # noqa: F403

DEBUG = False

# Speed up password hashing in tests; the hashing itself is not under test.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
