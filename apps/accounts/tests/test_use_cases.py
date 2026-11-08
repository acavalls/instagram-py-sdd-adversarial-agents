import pytest

from apps.accounts.models import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_USERNAME_ALREADY_TAKEN,
    User,
)
from apps.accounts.services import UserService
from apps.accounts.use_cases import (
    ERROR_INVALID_CREDENTIALS,
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)


def _execute(username: str, email: str, password: str = "password123"):
    return RegisterUserUseCase(UserService()).execute(
        RegisterUserInput(username=username, email=email, password=password)
    )


@pytest.mark.django_db
class TestRegisterUserUseCase:
    def test_successful_registration(self) -> None:
        output = _execute("alice", "alice@example.com")

        assert output.success and output.error is None
        assert output.user is not None
        assert output.user.username == "alice"
        assert output.user.email == "alice@example.com"
        assert output.user.check_password("password123")
        assert User.objects.count() == 1

    def test_duplicate_email_rejected(self) -> None:
        _execute("alice", "alice@example.com")

        output = _execute("bob", "alice@example.com")

        assert not output.success
        assert output.error == ERROR_EMAIL_ALREADY_REGISTERED
        assert User.objects.count() == 1

    def test_duplicate_username_rejected(self) -> None:
        _execute("alice", "alice@example.com")

        output = _execute("alice", "bob@example.com")

        assert not output.success
        assert output.error == ERROR_USERNAME_ALREADY_TAKEN
        assert User.objects.count() == 1

    def test_concurrent_duplicate_registration_keeps_data_consistent(self, mocker) -> None:
        """A race past the explicit check lands on the DB unique constraint."""
        _execute("alice", "alice@example.com")
        mocker.patch.object(User, "validate_registration", lambda *args, **kwargs: None)

        output = _execute("alice", "alice@example.com")

        assert not output.success
        assert output.error == ERROR_EMAIL_ALREADY_REGISTERED
        assert User.objects.count() == 1

    def test_concurrent_duplicate_username_keeps_data_consistent(self, mocker) -> None:
        _execute("alice", "alice@example.com")
        mocker.patch.object(User, "validate_registration", lambda *args, **kwargs: None)

        output = _execute("alice", "other@example.com")

        assert not output.success
        assert output.error == ERROR_USERNAME_ALREADY_TAKEN
        assert User.objects.count() == 1


def _authenticate(username: str, password: str):
    return AuthenticateUserUseCase().execute(
        AuthenticateUserInput(username=username, password=password)
    )


@pytest.mark.django_db
class TestAuthenticateUserUseCase:
    def test_successful_authentication(self) -> None:
        _execute("alice", "alice@example.com")

        output = _authenticate("alice", "password123")

        assert output.success and output.error is None
        assert output.user is not None
        assert output.user.username == "alice"

    def test_unknown_user_fails_with_generic_error(self) -> None:
        output = _authenticate("nobody", "password123")

        assert not output.success
        assert output.error == ERROR_INVALID_CREDENTIALS

    def test_blank_credentials_fail_with_generic_error(self) -> None:
        for username, password in [("", "password123"), ("alice", ""), ("", "")]:
            output = _authenticate(username, password)

            assert not output.success
            assert output.error == ERROR_INVALID_CREDENTIALS

    def test_login_password_is_byte_exact(self) -> None:
        """Password comparison is byte-exact at the authentication layer."""
        stored_password = "  Password123  "
        _execute("alice", "alice@example.com", password=stored_password)

        for submitted in [
            stored_password.strip(),
            "  password123  ",
            "  PASSWORD123  ",
            "Password123",
            "password123",
        ]:
            output = _authenticate("alice", submitted)

            assert not output.success
            assert output.error == ERROR_INVALID_CREDENTIALS

        output = _authenticate("alice", stored_password)

        assert output.success
