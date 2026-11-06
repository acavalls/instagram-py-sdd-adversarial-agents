"""User model for the accounts domain."""

import re
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150

USERNAME_FORMAT_ERROR = "Username must contain only letters and numbers"
USERNAME_LENGTH_ERROR = "Username must be between 3 and 150 characters"
USERNAME_TAKEN_ERROR = "Username already taken"
EMAIL_TAKEN_ERROR = "Email already registered"

PASSWORD_MIN_LENGTH = 8
PASSWORD_TOO_SHORT_ERROR = "Password must be at least 8 characters"

_USERNAME_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class User(AbstractUser):
    """Application user: UUID identity, unique email and profile fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, default="")
    profile_pic = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def validate_username_format(cls, username: str) -> str | None:
        """Validate the username format rules (length and alphanumeric).

        Returns the explicit error message for the first rule broken, or
        ``None`` when the username is well-formed.
        """
        if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
            return USERNAME_LENGTH_ERROR
        if _USERNAME_PATTERN.fullmatch(username) is None:
            return USERNAME_FORMAT_ERROR
        return None

    @classmethod
    def validate_registration(cls, *, username: str, email: str) -> str | None:
        """Validate registration data against the spec rules.

        Checks the username format (alphanumeric, 3-150 characters) and the
        identity-duplicate rules (unique username, unique email). Returns the
        explicit error message for the first rule broken, or ``None`` when the
        data is valid (errors-as-strings, per design decision 6).
        """
        format_error = cls.validate_username_format(username)
        if format_error is not None:
            return format_error
        if cls._default_manager.filter(username=username).exists():
            return USERNAME_TAKEN_ERROR
        if cls._default_manager.filter(email=email).exists():
            return EMAIL_TAKEN_ERROR
        return None
