import re
import threading
import uuid
from typing import ClassVar

from django.contrib.auth.hashers import identify_hasher, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models

ERROR_USERNAME_NOT_ALPHANUMERIC = "Username must contain only letters and numbers"
ERROR_USERNAME_TOO_SHORT = "Username must be at least 3 characters"
ERROR_USERNAME_TOO_LONG = "Username must be 150 characters or fewer"
ERROR_USERNAME_ALREADY_TAKEN = "Username already taken"
ERROR_EMAIL_ALREADY_REGISTERED = "Email already registered"

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150


def validate_username(value: object) -> None:
    """The model's username validation error: `django.core.exceptions.ValidationError`."""
    if not isinstance(value, str) or not USERNAME_PATTERN.fullmatch(value):
        raise ValidationError(ERROR_USERNAME_NOT_ALPHANUMERIC)
    if len(value) < USERNAME_MIN_LENGTH:
        raise ValidationError(ERROR_USERNAME_TOO_SHORT)
    if len(value) > USERNAME_MAX_LENGTH:
        raise ValidationError(ERROR_USERNAME_TOO_LONG)


def _validate_bulk_username(value: object) -> None:
    """Validate the username carried by a bulk write.

    Non-literal values (expressions, missing text) are refused with the
    same model username validation error as invalid literals.
    """
    validate_username(value)


_bulk_write_state = threading.local()


def _internal_bulk_write_active() -> bool:
    return getattr(_bulk_write_state, "active", False)


class UserQuerySet(models.QuerySet):
    """QuerySet that enforces the username rule on every bulk write path."""

    def create(self, **kwargs):  # type: ignore[override]
        if "username" in kwargs:
            _validate_bulk_username(kwargs["username"])
        return super().create(**kwargs)

    def update(self, **kwargs) -> int:
        if "username" in kwargs and not _internal_bulk_write_active():
            _validate_bulk_username(kwargs["username"])
        return super().update(**kwargs)

    def bulk_create(self, objs, *args, **kwargs):  # type: ignore[override]
        for obj in objs:
            _validate_bulk_username(obj.username)
        return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):  # type: ignore[override]
        if "username" in fields:
            for obj in objs:
                _validate_bulk_username(obj.username)
        previous_state = getattr(_bulk_write_state, "active", False)
        _bulk_write_state.active = True
        try:
            return super().bulk_update(objs, fields, *args, **kwargs)
        finally:
            _bulk_write_state.active = previous_state


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):  # type: ignore[misc]
    """Default manager with bulk-write username enforcement."""

    def _create_user(self, username: str, email: str | None, password: str | None, **extra_fields):  # type: ignore[override]
        validate_username(username)
        if email:
            validate_email(email)
        user = self.model(
            username=username, email=self.normalize_email(email or ""), **extra_fields
        )
        user.password = make_password(password)
        user.save(using=self._db)
        return user


class User(AbstractUser):
    """App user: UUID identity with a unique email and an optional profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        "username",
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[validate_username],
        help_text="Required. 3 to 150 characters. Letters and numbers only.",
        error_messages={"unique": ERROR_USERNAME_ALREADY_TAKEN},
    )
    email = models.EmailField("email address", unique=True)
    bio = models.TextField("bio", blank=True, default="")
    profile_pic = models.ImageField(
        "profile picture", upload_to="profile_pics/", blank=True, null=True
    )
    updated_at = models.DateTimeField("updated at", auto_now=True)

    objects: ClassVar[UserManager] = UserManager()

    def __str__(self) -> str:
        return self.username

    def save(self, *args, **kwargs):
        """Enforce the username and password rules on the direct storage path.

        The field validators already run through `full_clean` and the
        bulk-write interception covers the queryset paths; this override
        closes the remaining gap so a plain `instance.save()` cannot store
        a username that violates the username rule (the write is refused)
        nor a plain-text password (it is hashed before persisting, byte-
        exactly, with no trimming or case folding).
        """
        try:
            validate_username(self.username)
        except ValidationError:
            return
        if self._password_needs_hashing():
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def _password_needs_hashing(self) -> bool:
        if not self.password:
            return False
        try:
            identify_hasher(self.password)
        except ValueError:
            return True
        return False

    @classmethod
    def validate_registration(cls, *, username: str, email: str) -> None:
        """Model validation used by the registration use case.

        Enforces the username rule (the same field validator) and the
        identity-duplicate rules with explicit messages. Uniqueness is
        ultimately guaranteed by the database unique constraints, which
        guard against concurrent registration attempts.
        """
        validate_username(username)
        if cls._default_manager.filter(username=username).exists():
            raise ValidationError({"username": [ERROR_USERNAME_ALREADY_TAKEN]})
        if cls._default_manager.filter(email=email).exists():
            raise ValidationError({"email": [ERROR_EMAIL_ALREADY_REGISTERED]})
