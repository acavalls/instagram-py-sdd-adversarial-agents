"""User model for the accounts domain."""

import re
import uuid
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150

USERNAME_FORMAT_ERROR = "Username must contain only letters and numbers"
USERNAME_LENGTH_ERROR = "Username must be between 3 and 150 characters"
USERNAME_TAKEN_ERROR = "Username already taken"
EMAIL_TAKEN_ERROR = "Email already registered"

PASSWORD_MIN_LENGTH = 8
PASSWORD_TOO_SHORT_ERROR = "Password must be at least 8 characters"

_USERNAME_PATTERN = re.compile(r"[a-zA-Z0-9]+")

# Model-level alphanumeric rule (DRIFT-002): shared by the field validators
# below and by the API serializer so every creation path enforces the same
# rule with the same message. ``\A``/``\Z`` anchors (instead of ``^``/``$``)
# close the "$ matches before a trailing newline" hole.
USERNAME_ALPHANUMERIC_VALIDATOR = RegexValidator(
    regex=r"\A[a-zA-Z0-9]+\Z",
    message=USERNAME_FORMAT_ERROR,
)


class UserManager(DjangoUserManager["User"]):
    """User manager that keeps the username rule un-bypassable (DRIFT-002).

    ``BaseUserManager.create_user`` never runs field validators or
    ``full_clean()``, so without this override the shell/fixtures path
    (``create_user``/``create_superuser``) would persist a hostile username.
    Following the project's errors-as-values style (design decision 6), an
    invalid username neither raises nor persists: a detached instance is
    returned and nothing is written. The instance cannot leak into storage
    later either — ``User.save`` below refuses to persist it.
    """

    def create_user(
        self,
        username: str,
        email: str | None = None,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        if User.validate_username_format(username) is not None:
            # Detached (never persisted) instance; ``User.save`` would still
            # refuse to store it if a caller ever tried.
            instance = self.model(username=username, **extra_fields)
            if email is not None:
                instance.email = email
            return instance
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(
        self,
        username: str,
        email: str | None = None,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """Create a superuser under the same username contract as ``create_user``.

        Django's ``contrib`` ``UserManager.create_superuser`` calls
        ``_create_user`` directly, bypassing our ``create_user`` override, so
        a hostile username would reach ``User.save`` and raise instead of
        following the errors-as-values contract. This override replicates
        Django's superuser flag handling (``setdefault`` for ``is_staff``/
        ``is_superuser``/``is_active``, ``ValueError`` when they are passed
        explicitly falsy) and then delegates through ``create_user`` so
        username validation and the detached-instance behavior are shared.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """Application user: UUID identity, unique email and profile fields."""

    # The rule-enforcing manager (create_user/create_superuser cannot bypass
    # the username rule).
    objects: ClassVar[UserManager] = UserManager()

    # Redeclared (instead of only overriding ``username_validator``) because
    # AbstractUser builds its ``username`` field — with its permissive
    # validator — at class-creation time; redeclaring is the deterministic
    # way to enforce the alphanumeric rule on every creation path (admin,
    # shell, fixtures). All other AbstractUser username semantics are kept.
    # The min length is an explicit validator (max length is intrinsic to
    # ``max_length``); together with the regex they make ``full_clean()`` and
    # ``validate_username_format()`` agree on every hostile input.
    username = models.CharField(
        _("username"),
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters and digits only."),
        validators=[MinLengthValidator(USERNAME_MIN_LENGTH), USERNAME_ALPHANUMERIC_VALIDATOR],
        error_messages={"unique": _("A user with that username already exists.")},
    )

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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Enforce the username format rule on EVERY persistence path.

        ``UserManager.create_user`` (shell, fixtures, services) and a bare
        ``User(...).save()`` never run field validators or ``full_clean()``
        (Django semantics), so the alphanumeric rule would be bypassed there.
        Model forms / the admin already validate through ``full_clean()``,
        which runs this same rule via the field validators. The check is
        targeted to the username only — the password hash and every other
        field keep plain Django save semantics.
        """
        error = self.validate_username_format(self.username)
        if error is not None:
            raise ValidationError({"username": [error]})
        super().save(*args, **kwargs)

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
