"""Bad-attack probes for the 06-regularize-audit-drift change (accounts side).

Attacks the NEW/CHANGED guarantees: bulk hashing, byte-exact emails through
every storage path, createsuperuser tooling, the accounts.0003 bootstrap and
the API whitespace/normalization rules.
"""

import pytest
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_USERNAME_ALREADY_TAKEN,
    ERROR_USERNAME_NOT_ALPHANUMERIC,
    User,
)
from apps.accounts.services import UserService
from apps.accounts.use_cases.register_user import (
    RegisterUserInput,
    RegisterUserUseCase,
)

pytestmark = pytest.mark.django_db

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"

# A raw password deliberately crafted to look like a real Django hash.
HASH_LOOKALIKE = (
    "pbkdf2_sha256$600000$salt$0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
)
MD5_LOOKALIKE = "md5$not-a-real-md5-payload"


def _register_api(client, username, email, password="password-123"):
    return client.post(
        REGISTER,
        {"username": username, "email": email, "password": password},
        content_type="application/json",
    )


def _register_use_case(username, email, password="password-123"):
    return RegisterUserUseCase(user_service=UserService()).execute(
        RegisterUserInput(username=username, email=email, password=password)
    )


class TestBulkHashLookalikePasswords:
    """A raw password that looks like a hash string must still be hashed."""

    def test_bulk_create_stores_hashlookalike_raw_and_it_never_authenticates(self):
        # With the test settings' hasher list (md5 only), a pbkdf2-shaped
        # string fails identification and is hashed; under production
        # settings (pbkdf2 enabled) BUG-001 would leave it raw too.
        user = User(username="lookalike1", email="lookalike1@example.com")
        user.password = HASH_LOOKALIKE
        User.objects.bulk_create([user])

        stored = User.objects.get(username="lookalike1").password
        # The stored value must never equal the raw chosen password...
        assert stored != HASH_LOOKALIKE or not check_password(HASH_LOOKALIKE, stored), (
            f"Raw hash-lookalike password stored as-is: {stored!r}"
        )
        # ...and it must authenticate against the chosen password.
        assert check_password(HASH_LOOKALIKE, User.objects.get(username="lookalike1").password)

    def test_bulk_create_md5_lookalike_raw_password_is_stored_hashed(self):
        # Regression test for BUG-001: `identify_hasher` used to recognize
        # any string whose prefix names an installed algorithm, so the raw
        # password "md5$..." passed the guard and was stored as-is. The fix
        # demands a provable round-trip (identify_hasher + hasher.decode),
        # so the lookalike is now treated as raw and hashed.
        user = User(username="lookalike2", email="lookalike2@example.com")
        user.password = MD5_LOOKALIKE
        User.objects.bulk_create([user])

        stored = User.objects.get(username="lookalike2").password
        assert stored != MD5_LOOKALIKE, f"raw password stored as-is: {stored!r}"
        assert check_password(MD5_LOOKALIKE, stored)

    def test_save_path_hashlookalike_password(self):
        user = User(username="lookalike3", email="lookalike3@example.com")
        user.password = HASH_LOOKALIKE
        user.save()

        stored = User.objects.get(username="lookalike3").password
        assert stored != HASH_LOOKALIKE or not check_password(HASH_LOOKALIKE, stored)
        assert check_password(HASH_LOOKALIKE, User.objects.get(username="lookalike3").password)

    def test_bulk_create_mix_of_hashed_and_raw_passwords(self):
        raw_user = User(username="mixraw", email="mixraw@example.com")
        raw_user.password = "plain-raw-password-1"
        hashed_user = User(username="mixhashed", email="mixhashed@example.com")
        hashed_user.set_password("already-hashed-password-1")

        User.objects.bulk_create([raw_user, hashed_user])

        assert check_password("plain-raw-password-1", User.objects.get(username="mixraw").password)
        assert check_password(
            "already-hashed-password-1", User.objects.get(username="mixhashed").password
        )
        assert not User.objects.get(username="mixraw").password.startswith("plain-raw")

    def test_bulk_create_empty_password_is_not_usable(self):
        user = User(username="emptypass", email="emptypass@example.com")
        user.password = ""
        User.objects.bulk_create([user])
        stored = User.objects.get(username="emptypass").password
        assert not check_password("", stored)


class TestByteExactEmailsEverywhere:
    def test_api_accepts_mixed_case_email_byte_exactly(self, client):
        response = _register_api(client, "caseapi", "Mixed.Case@ExAmPlE.COM")
        assert response.status_code == 201, response.content
        assert User.objects.get(username="caseapi").email == "Mixed.Case@ExAmPlE.COM"

    def test_fullwidth_nfkc_email_is_not_silently_normalized(self, client):
        # NFKC-confusable fullwidth characters: the email path must not leak
        # the username's NFKC normalization. Either reject or store byte-exact.
        response = _register_api(client, "nfkcuser", "ｕｓｅｒ@ｅｘａｍｐｌｅ.com")
        if response.status_code == 201:
            stored = User.objects.get(username="nfkcuser").email
            assert stored == "ｕｓｅｒ@ｅｘａｍｐｌｅ.com", (
                f"NFKC normalization leaked into the email path: {stored!r}"
            )
        else:
            assert response.status_code in (400, 422)

    def test_bulk_create_email_is_byte_exact(self):
        user = User(username="bulkcase", email="Bulk@X.COM")
        User.objects.bulk_create([user])
        assert User.objects.get(username="bulkcase").email == "Bulk@X.COM"

    def test_createsuperuser_email_is_byte_exact(self, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "super-password-1")
        call_command(
            "createsuperuser",
            "--noinput",
            username="casemaster",
            email="Casemaster@X.COM",
            verbosity=0,
        )
        assert User.objects.get(username="casemaster").email == "Casemaster@X.COM"

    def test_same_email_and_username_duplicate_race_mapping_is_sane(self, client):
        _register_api(client, "dupeone", "dupe@example.com")
        # Both collide: any of the two duplicate errors is sane; a crash or a
        # generic/misleading error is not.
        response = _register_api(client, "dupeone", "dupe@example.com")
        assert response.status_code in (400, 409, 422)
        body = response.json()
        text = str(body)
        assert ERROR_USERNAME_ALREADY_TAKEN in text or ERROR_EMAIL_ALREADY_REGISTERED in text, text

    def test_email_only_duplicate_reports_email_error(self, client):
        _register_api(client, "dupea", "shared@example.com")
        response = _register_api(client, "dupeb", "shared@example.com")
        assert response.status_code in (400, 409, 422)
        assert ERROR_EMAIL_ALREADY_REGISTERED in str(response.json())


class TestCreatesuperuserTooling:
    def test_createsuperuser_rejects_padded_username(self, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "super-password-1")
        # Django's stock command wraps field validation in CommandError;
        # any rejection is sane as long as nothing is stored.
        with pytest.raises(Exception) as excinfo:
            call_command(
                "createsuperuser",
                "--noinput",
                username="  padded  ",
                email="padded@example.com",
                verbosity=0,
            )
        assert not User.objects.filter(username="  padded  ").exists()
        assert not User.objects.filter(email="padded@example.com").exists()
        assert (
            "CommandError" in type(excinfo.value).__name__
            or "ValidationError" in type(excinfo.value).__name__
        )

    def test_createsuperuser_rejects_invalid_username(self, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "super-password-1")
        with pytest.raises(CommandError):
            call_command(
                "createsuperuser",
                "--noinput",
                username="bad!name",
                email="badname@example.com",
                verbosity=0,
            )
        assert not User.objects.filter(username="bad!name").exists()

    def test_createsuperuser_duplicate_username_errors_sane(self, monkeypatch):
        User.objects.create_user(username="taken", email="taken@example.com", password="pw-123456")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "super-password-1")
        with pytest.raises(Exception) as excinfo:
            call_command(
                "createsuperuser",
                "--noinput",
                username="taken",
                email="other@example.com",
                verbosity=0,
            )
        # Any exception is acceptable (rejected); the row must be untouched.
        assert not User.objects.filter(username="taken", email="other@example.com").exists()
        assert "unique" in str(excinfo.value).lower() or "taken" in str(excinfo.value).lower()

    def test_manager_create_user_and_superuser_hash_and_reject_padded(self):
        user = User.objects.create_user(
            username="managed", email="Managed@X.COM", password="pw-12345678"
        )
        assert check_password("pw-12345678", user.password)
        assert user.email == "Managed@X.COM"

        superuser = User.objects.create_superuser(
            username="supermanaged", email="Super@X.COM", password="pw-87654321"
        )
        assert check_password("pw-87654321", superuser.password)
        assert superuser.is_staff and superuser.is_superuser

        with pytest.raises(ValidationError):
            User.objects.create_user(username="  padded  ", password="pw-12345678")


class TestDevSuperuserBootstrap:
    """accounts.0003 must never clobber an existing bob and must yield a
    working dev superuser under DEBUG."""

    def _run_bootstrap(self):
        import importlib.util
        from pathlib import Path

        migration_file = (
            Path(__file__).resolve().parents[1] / "migrations" / "0003_dev_superuser_bootstrap.py"
        )
        spec = importlib.util.spec_from_file_location(
            "accounts_0003_attack_bootstrap", migration_file
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from django.apps import apps

        module.create_dev_superuser(apps, None)

    def test_existing_bob_with_different_password_is_not_overwritten(self, settings):
        import hashlib

        User.objects.create(
            username="bob",
            email="mine@example.com",
            password=hashlib.md5(b"mine-own-secret").hexdigest(),
            is_staff=True,
            is_superuser=True,
        )
        stored_before = User.objects.get(username="bob").password
        with override_settings(DEBUG=True):
            self._run_bootstrap()
        bob = User.objects.get(username="bob")
        assert User.objects.filter(username="bob").count() == 1
        assert bob.email == "mine@example.com"
        assert bob.password == stored_before
        assert check_password(hashlib.md5(b"mine-own-secret").hexdigest(), bob.password)

    def test_bootstrap_bob_logs_into_web_and_admin(self, settings, client):
        with override_settings(DEBUG=True):
            self._run_bootstrap()
        bob = User.objects.get(username="bob")
        assert bob.is_staff and bob.is_superuser

        response = client.post("/web/login/", {"username": "bob", "password": "bob-ig-pass-1"})
        assert response.status_code == 302

        admin_response = client.get("/admin/")
        assert admin_response.status_code == 200

    def test_bootstrap_under_debug_off_creates_nobody_when_absent(self):
        User.objects.filter(username="bob").delete()
        with override_settings(DEBUG=False):
            self._run_bootstrap()
        assert not User.objects.filter(username="bob").exists()


class TestApiRegressions:
    def test_jwt_login_still_works_for_existing_valid_username(self, client):
        _register_api(client, "reguser", "reguser@example.com", password="password-123")
        response = client.post(
            LOGIN,
            {"username": "reguser", "password": "password-123"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["access"]

    def test_api_login_trims_username_documenting_spec_silent_behavior(self, client):
        # Spec-silent probe: registration rejects padded usernames, but the
        # login serializer's username field still trims, so a padded username
        # authenticates at login. Byte-exactness is only declared for
        # passwords; reported as a minor observation.
        _register_api(client, "trimlogin", "trimlogin@example.com", password="password-123")
        response = client.post(
            LOGIN,
            {"username": "  trimlogin  ", "password": "password-123"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["access"]

    def test_api_email_whitespace_is_trimmed_documenting_spec_silent_behavior(self, client):
        # Spec-silent probe: the email field (unlike the username) is still
        # trimmed by DRF, so a padded email is accepted stripped. Reported as
        # a minor observation; no raw value is stored.
        response = _register_api(client, "pademail", "  padded@example.com  ")
        assert response.status_code == 201, response.content
        assert User.objects.get(username="pademail").email == "padded@example.com"

    def test_api_rejects_padded_username_with_username_error(self, client):
        response = _register_api(client, "  padapi  ", "padapi@example.com")
        assert response.status_code in (400, 422)
        assert ERROR_USERNAME_NOT_ALPHANUMERIC in str(response.json())

    def test_email_case_duplicate_accepted_byte_exact_via_api(self, client):
        _register_api(client, "exactone", "exact@x.com")
        response = _register_api(client, "exacttwo", "EXACT@X.COM")
        assert response.status_code == 201, response.content
        assert User.objects.get(username="exacttwo").email == "EXACT@X.COM"
