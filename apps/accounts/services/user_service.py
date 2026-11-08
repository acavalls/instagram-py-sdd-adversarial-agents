from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User


@dataclass(frozen=True, slots=True)
class CreateUserOutput:
    """Result of creating a user account."""

    success: bool
    user: User | None = None
    error: str | None = None


class UserService:
    """Domain service for user account persistence."""

    def create_user(self, *, username: str, email: str, password: str) -> CreateUserOutput:
        """Create a user with a hashed password after model validation.

        The password is hashed byte-exactly (no trimming or case folding).
        Model validation runs on the instance; duplicate identities are
        refused with explicit error strings. A race past the duplicate
        check surfaces as IntegrityError from the database unique
        constraints and is left to the calling use case to map.
        """
        user = User(username=username, email=email)
        user.set_password(password)
        try:
            user.full_clean(validate_unique=False, validate_constraints=False)
        except ValidationError as exc:
            return CreateUserOutput(success=False, error=self._first_error(exc))
        with transaction.atomic():
            user.save()
        return CreateUserOutput(success=True, user=user)

    @staticmethod
    def _first_error(exc: ValidationError) -> str:
        for message in exc.messages:
            if isinstance(message, str):
                return message
        return "Invalid data"
