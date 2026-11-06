"""Use cases for the accounts domain (application layer)."""

from dataclasses import dataclass

from django.contrib.auth import authenticate

from apps.accounts.models import User
from apps.accounts.services import UserService

# Generic login error: any failure (unknown username OR wrong password)
# reports exactly this message so the cause is never revealed (spec:
# "Failed web login hides the cause").
INVALID_CREDENTIALS_ERROR = "Invalid credentials"


@dataclass(frozen=True, slots=True)
class RegisterUserInput:
    """Input DTO for the registration use case."""

    username: str
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RegisterUserOutput:
    """Output DTO for the registration use case (errors as strings)."""

    success: bool
    user: User | None = None
    error: str | None = None


class RegisterUserUseCase:
    """Register a new user with duplicate identity validation."""

    def __init__(self, user_service: UserService | None = None) -> None:
        self._user_service = user_service or UserService()

    def execute(self, input_dto: RegisterUserInput) -> RegisterUserOutput:
        """Create the account, returning an explicit failure output on error."""
        user, error = self._user_service.create_user(
            username=input_dto.username,
            email=input_dto.email,
            password=input_dto.password,
        )
        if error is not None:
            return RegisterUserOutput(success=False, error=error)
        return RegisterUserOutput(success=True, user=user)


@dataclass(frozen=True, slots=True)
class AuthenticateUserInput:
    """Input DTO for the authentication use case (login by username)."""

    username: str
    password: str


@dataclass(frozen=True, slots=True)
class AuthenticateUserOutput:
    """Output DTO for the authentication use case (errors as strings)."""

    success: bool
    user: User | None = None
    error: str | None = None


class AuthenticateUserUseCase:
    """Authenticate an existing user by username and password."""

    def execute(self, input_dto: AuthenticateUserInput) -> AuthenticateUserOutput:
        """Verify the credentials via ``django.contrib.auth`` (design decision 4).

        Any failure — unknown username or wrong password — yields the same
        generic error so the cause is never revealed.
        """
        user = authenticate(username=input_dto.username, password=input_dto.password)
        if user is None:
            return AuthenticateUserOutput(success=False, error=INVALID_CREDENTIALS_ERROR)
        return AuthenticateUserOutput(success=True, user=user)
