import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.models import F, Value

from apps.accounts.models import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_USERNAME_ALREADY_TAKEN,
    ERROR_USERNAME_NOT_ALPHANUMERIC,
    ERROR_USERNAME_TOO_LONG,
    ERROR_USERNAME_TOO_SHORT,
    User,
    validate_username,
)
from apps.accounts.services import UserService
from apps.accounts.use_cases import RegisterUserInput, RegisterUserUseCase


def _register(username: str, email: str, password: str = "password123"):
    return RegisterUserUseCase(UserService()).execute(
        RegisterUserInput(username=username, email=email, password=password)
    )


class TestUsernameFormatValidation:
    @pytest.mark.parametrize(
        ("username", "expected_message"),
        [
            ("ab", ERROR_USERNAME_TOO_SHORT),
            ("a" * 151, ERROR_USERNAME_TOO_LONG),
            ("user!", ERROR_USERNAME_NOT_ALPHANUMERIC),
            ("", ERROR_USERNAME_NOT_ALPHANUMERIC),
        ],
    )
    def test_username_format_validation(self, username: str, expected_message: str) -> None:
        with pytest.raises(ValidationError, match=expected_message):
            validate_username(username)

    def test_registration_rejects_invalid_username_format(self, db) -> None:
        output = _register("ab", "short@example.com")
        assert not output.success
        assert output.error == ERROR_USERNAME_TOO_SHORT


class TestUserAccountPersisted:
    @pytest.mark.django_db
    def test_user_account_persisted(self) -> None:
        output = _register("alice", "alice@example.com")

        assert output.success and output.user is not None
        user = output.user
        assert isinstance(user.id, uuid.UUID)
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.bio == ""
        assert not user.profile_pic
        assert user.password != "password123"
        assert user.check_password("password123")

    @pytest.mark.django_db
    def test_username_and_email_are_unique(self) -> None:
        _register("alice", "alice@example.com")

        assert User._meta.get_field("username").unique
        assert User._meta.get_field("email").unique


class TestBulkWritesEnforceTheUsernameRule:
    @pytest.mark.django_db
    def test_bulk_writes_enforce_the_username_rule_update(self) -> None:
        _register("alice", "alice@example.com")
        user = User.objects.get(username="alice")

        with pytest.raises(ValidationError) as excinfo:
            User.objects.filter(pk=user.pk).update(username="bad name!")
        assert str(excinfo.value.messages[0]) == ERROR_USERNAME_NOT_ALPHANUMERIC
        user.refresh_from_db()
        assert user.username == "alice"

    @pytest.mark.django_db
    def test_bulk_writes_enforce_the_username_rule_bulk_create(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            User.objects.bulk_create(
                [User(username="no!", email="nobody@example.com", password="x")]
            )
        assert str(excinfo.value.messages[0]) == ERROR_USERNAME_NOT_ALPHANUMERIC
        assert not User.objects.filter(email="nobody@example.com").exists()

    @pytest.mark.django_db
    def test_bulk_writes_enforce_the_username_rule_bulk_update(self) -> None:
        _register("alice", "alice@example.com")
        user = User.objects.get(username="alice")
        user.username = "ab"

        with pytest.raises(ValidationError) as excinfo:
            User.objects.bulk_update([user], ["username"])
        assert str(excinfo.value.messages[0]) == ERROR_USERNAME_TOO_SHORT
        user.refresh_from_db()
        assert user.username == "alice"


class TestNonLiteralUsernameWriteRefused:
    @pytest.mark.django_db
    def test_non_literal_username_write_refused_update_expression(self) -> None:
        _register("alice", "alice@example.com")
        user = User.objects.get(username="alice")

        with pytest.raises(ValidationError, match=ERROR_USERNAME_NOT_ALPHANUMERIC):
            User.objects.filter(pk=user.pk).update(username=F("email"))

        with pytest.raises(ValidationError, match=ERROR_USERNAME_NOT_ALPHANUMERIC):
            User.objects.filter(pk=user.pk).update(username=Value("newname1"))

        user.refresh_from_db()
        assert user.username == "alice"

    @pytest.mark.django_db
    def test_non_literal_username_write_refused_bulk_create_missing_value(self) -> None:
        ghost = User(email="ghost@example.com")
        ghost.username = None  # type: ignore[assignment]

        with pytest.raises(ValidationError, match=ERROR_USERNAME_NOT_ALPHANUMERIC):
            User.objects.bulk_create([ghost])


class TestLegalUsernameBulkWriteApplies:
    @pytest.mark.django_db
    def test_legal_username_bulk_write_applies_update(self) -> None:
        _register("alice", "alice@example.com")
        user = User.objects.get(username="alice")

        updated = User.objects.filter(pk=user.pk).update(username="newname1")

        assert updated == 1
        user.refresh_from_db()
        assert user.username == "newname1"

    @pytest.mark.django_db
    def test_legal_username_bulk_write_applies_bulk_update(self) -> None:
        _register("alice", "alice@example.com")
        user = User.objects.get(username="alice")
        user.username = "newname2"

        User.objects.bulk_update([user], ["username"])

        user.refresh_from_db()
        assert user.username == "newname2"

    @pytest.mark.django_db
    def test_legal_username_bulk_write_applies_bulk_create(self) -> None:
        created = User.objects.bulk_create(
            [User(username="bulkuser1", email="bulk1@example.com", password="x")]
        )

        assert User.objects.filter(username="bulkuser1").exists()
        assert created[0].username == "bulkuser1"

    @pytest.mark.django_db
    def test_legal_username_manager_create_applies(self) -> None:
        user = User.objects.create(username="created1", email="created1@example.com", password="x")

        assert user.pk is not None
        assert User.objects.filter(username="created1").exists()


class TestPasswordComparisonIsByteExact:
    @pytest.mark.django_db
    def test_password_comparison_is_byte_exact(self) -> None:
        output = UserService().create_user(
            username="bob", email="bob@example.com", password=" Secret Pass "
        )

        assert output.success and output.user is not None
        user = output.user
        assert user.check_password(" Secret Pass ")
        assert not user.check_password("Secret Pass")
        assert not user.check_password(" secret pass ")
        assert not user.check_password("SECRET PASS")

    @pytest.mark.django_db
    def test_model_validation_never_touches_the_password(self) -> None:
        output = UserService().create_user(username="bob", email="bob@example.com", password="  ")

        assert output.success and output.user is not None
        assert output.user.check_password("  ")
        assert not output.user.check_password("")


class TestModelValidation:
    @pytest.mark.django_db
    def test_validate_registration_reports_username_taken(self) -> None:
        _register("alice", "alice@example.com")

        with pytest.raises(ValidationError) as excinfo:
            User.validate_registration(username="alice", email="other@example.com")

        assert str(excinfo.value.message_dict["username"][0]) == ERROR_USERNAME_ALREADY_TAKEN

    @pytest.mark.django_db
    def test_validate_registration_reports_email_registered(self) -> None:
        _register("alice", "alice@example.com")

        with pytest.raises(ValidationError) as excinfo:
            User.validate_registration(username="bob", email="alice@example.com")

        assert str(excinfo.value.message_dict["email"][0]) == ERROR_EMAIL_ALREADY_REGISTERED
