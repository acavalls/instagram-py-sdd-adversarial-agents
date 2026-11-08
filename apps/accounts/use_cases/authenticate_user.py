from dataclasses import dataclass
from typing import cast

from django.contrib.auth import authenticate

from apps.accounts.models import User

ERROR_INVALID_CREDENTIALS = "Invalid credentials"


@dataclass(frozen=True, slots=True)
class AuthenticateUserInput:
    """Login data submitted by an adapter (web view or API)."""

    username: str
    password: str


@dataclass(frozen=True, slots=True)
class AuthenticateUserOutput:
    """Result of checking login credentials."""

    success: bool
    user: User | None = None
    error: str | None = None


class AuthenticateUserUseCase:
    """Check username/password credentials for login.

    The password is compared byte-exactly by the password hasher (no
    whitespace trimming or case folding). Any failure — unknown user,
    wrong password, blank or missing fields — is reported with the single
    generic error so no field reveals why the login failed.
    """

    def execute(self, input_dto: AuthenticateUserInput) -> AuthenticateUserOutput:
        if not input_dto.username or not input_dto.password:
            return AuthenticateUserOutput(success=False, error=ERROR_INVALID_CREDENTIALS)
        user = cast(
            "User | None",
            authenticate(username=input_dto.username, password=input_dto.password),
        )
        if user is None:
            return AuthenticateUserOutput(success=False, error=ERROR_INVALID_CREDENTIALS)
        return AuthenticateUserOutput(success=True, user=user)
