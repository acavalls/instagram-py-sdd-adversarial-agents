from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.models import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_USERNAME_ALREADY_TAKEN,
    User,
)
from apps.accounts.services import UserService


@dataclass(frozen=True, slots=True)
class RegisterUserInput:
    """Registration data submitted by an adapter (web view or API)."""

    username: str
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RegisterUserOutput:
    """Result of registering a user account."""

    success: bool
    user: User | None = None
    error: str | None = None


class RegisterUserUseCase:
    """Register a new account after model (identity) validation.

    Field-format rules are checked by the adapters (web view / write
    serializer) before this use case is called. Identity-duplicate rules
    live in `User.validate_registration`; a race past that check is
    caught by the database unique constraints and mapped here to the
    explicit duplicate error.
    """

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def execute(self, input_dto: RegisterUserInput) -> RegisterUserOutput:
        try:
            User.validate_registration(username=input_dto.username, email=input_dto.email)
        except ValidationError as exc:
            return RegisterUserOutput(success=False, error=self._first_error(exc))
        try:
            result = self._user_service.create_user(
                username=input_dto.username,
                email=input_dto.email,
                password=input_dto.password,
            )
        except IntegrityError:
            return RegisterUserOutput(success=False, error=self._duplicate_error(input_dto))
        if not result.success or result.user is None:
            return RegisterUserOutput(success=False, error=result.error)
        return RegisterUserOutput(success=True, user=result.user)

    @staticmethod
    def _duplicate_error(input_dto: RegisterUserInput) -> str:
        """Map a race past the duplicate checks to the right error.

        Emails are stored byte-exactly, so the submitted email matches
        the stored value exactly; username and email duplicates are
        checked distinctly so an email collision can never be reported
        as a username collision (and vice versa).
        """
        if User._default_manager.filter(email=input_dto.email).exists():
            return ERROR_EMAIL_ALREADY_REGISTERED
        if User._default_manager.filter(username=input_dto.username).exists():
            return ERROR_USERNAME_ALREADY_TAKEN
        return ERROR_USERNAME_ALREADY_TAKEN

    @staticmethod
    def _first_error(exc: ValidationError) -> str:
        for message in exc.messages:
            if isinstance(message, str):
                return message
        return "Invalid data"
