import re
import threading
import uuid
from typing import ClassVar

from django.contrib.auth.hashers import make_password
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
            if obj._password_needs_hashing():
                obj.password = make_password(obj.password)
                obj._password_is_hash = True
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

    def create_user(  # type: ignore[override]
        self, username: str, email: str | None = None, password: str | None = None, **extra_fields
    ):
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(  # type: ignore[override]
        self, username: str, email: str | None = None, password: str | None = None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(username, email, password, **extra_fields)

    def _create_user(self, username: str, email: str | None, password: str | None, **extra_fields):  # type: ignore[override]
        validate_username(username)
        if email:
            validate_email(email)
        user = self.model(username=username, email=email or "", **extra_fields)
        user.set_password(password)
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

    # Password provenance tracking. `password` is a plain CharField, so a
    # raw value and an encoded hash are indistinguishable by shape; the
    # hashing decision therefore relies on explicit state instead of
    # string inspection:
    # - `_password_is_hash`: True only when the current value was produced
    #   by `set_password` (or explicitly marked by a trusted writer, e.g.
    #   the accounts.0003 bootstrap that assigns a pre-computed hash).
    # - `_original_password`: the value as loaded from the database, so a
    #   re-save of an unchanged loaded instance never re-hashes its stored
    #   hash.
    _password_is_hash = False
    _original_password: str | None = None

    def __str__(self) -> str:
        return self.username

    @classmethod
    def from_db(cls, db, field_names, values):  # type: ignore[override]
        instance = super().from_db(db, field_names, values)
        instance._original_password = instance.password
        return instance

    def refresh_from_db(self, using=None, fields=None):  # type: ignore[override]
        super().refresh_from_db(using=using, fields=fields)
        if fields is None or "password" in fields:
            self._original_password = self.password

    def set_password(self, raw_password: str | None) -> None:  # type: ignore[override]
        super().set_password(raw_password)
        self._password_is_hash = True

    def clean(self) -> None:
        """Keep the email byte-exact during model validation.

        `AbstractUser.clean` normalizes the email's domain to lowercase
        via `objects.normalize_email`, which would violate the
        byte-exact, case-sensitive email uniqueness rule; this override
        preserves the registrant's exact email (local part and domain)
        while keeping the username normalization.
        """
        self.username = self.normalize_username(self.username)

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
            self._password_is_hash = True
        super().save(*args, **kwargs)

    def _password_needs_hashing(self) -> bool:
        """Decide whether the password needs hashing on the storage path.

        The decision relies on provenance, not on string shape (a raw
        password can be crafted to look exactly like an encoded hash, so
        shape-based detection is unreliable):

        - a value produced by `set_password` (or explicitly marked as a
          trusted hash by a writer such as the accounts.0003 bootstrap) is
          already hashed;
        - a value loaded from the database and left unchanged is the
          stored hash already;
        - anything else (new instances, or a loaded instance whose
          password was replaced) is raw and MUST be hashed.
        """
        if not self.password:
            return False
        if self._password_is_hash:
            return False
        return self.password != self._original_password

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
