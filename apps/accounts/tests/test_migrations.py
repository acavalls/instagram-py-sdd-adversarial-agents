"""Scenario tests for the accounts.0003 dev-superuser bootstrap migration.

The migration function is exercised directly against the real model
registry so the same code path that `migrate` runs is proven.
"""

import importlib.util
from pathlib import Path

import pytest
from django.apps import apps
from django.contrib.auth.hashers import check_password
from django.test import override_settings

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

_MIGRATION_FILE = (
    Path(__file__).resolve().parents[1] / "migrations" / "0003_dev_superuser_bootstrap.py"
)
_spec = importlib.util.spec_from_file_location(
    "accounts_0003_dev_superuser_bootstrap", _MIGRATION_FILE
)
_migration_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_migration_module)

create_dev_superuser = _migration_module.create_dev_superuser
DEV_SUPERUSER_USERNAME = _migration_module.DEV_SUPERUSER_USERNAME
DEV_SUPERUSER_EMAIL = _migration_module.DEV_SUPERUSER_EMAIL
DEV_SUPERUSER_PASSWORD = _migration_module.DEV_SUPERUSER_PASSWORD


def _run_migration() -> None:
    create_dev_superuser(apps, None)


class TestDevSuperuserBootstrap:
    def test_migration_creates_bob_under_debug(self, settings) -> None:
        settings.DEBUG = True

        _run_migration()

        bob = User.objects.get(username=DEV_SUPERUSER_USERNAME)
        assert bob.email == DEV_SUPERUSER_EMAIL
        assert bob.is_staff and bob.is_superuser
        assert bob.password != DEV_SUPERUSER_PASSWORD
        assert check_password(DEV_SUPERUSER_PASSWORD, bob.password)

    def test_migration_creates_nobody_with_debug_off(self, settings) -> None:
        settings.DEBUG = False

        _run_migration()

        assert not User.objects.filter(username=DEV_SUPERUSER_USERNAME).exists()

    def test_migration_is_idempotent_when_bob_exists(self, settings) -> None:
        settings.DEBUG = True
        _run_migration()

        _run_migration()

        assert User.objects.filter(username=DEV_SUPERUSER_USERNAME).count() == 1

    @override_settings(DEBUG=True)
    def test_migration_respects_debug_via_settings_override(self) -> None:
        _run_migration()

        assert User.objects.filter(username=DEV_SUPERUSER_USERNAME).exists()
