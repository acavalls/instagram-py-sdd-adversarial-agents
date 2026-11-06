"""Services for the accounts domain: write operations on users."""

from apps.accounts.models import User


class UserService:
    """Domain operations for creating users (called by use cases)."""

    def create_user(
        self, *, username: str, email: str, password: str
    ) -> tuple[User | None, str | None]:
        """Create a user after validating the registration rules.

        Runs ``User.validate_registration`` (username format, unique username,
        unique email), then persists the user with a hashed password. Returns
        ``(user, None)`` on success or ``(None, error)`` with the explicit
        error message when validation fails (errors-as-strings, design
        decision 6).
        """
        error = User.validate_registration(username=username, email=email)
        if error is not None:
            return None, error
        user = User.objects.create_user(username=username, email=email, password=password)
        return user, None
