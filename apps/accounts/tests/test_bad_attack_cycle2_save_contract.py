"""Cycle 2 attack: the User.save() override fix surface (BUG-001 fix).

Attacks the silent-refusal contract, the plain-text hashing heuristic and
the legitimate creation flows that the override must not break.
"""

import pytest
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


class TestSaveSilentRefusalContract:
    def test_save_with_invalid_username_does_not_persist_and_does_not_raise(self, db):
        user = User(username="bad name!", email="x@example.com")
        user.set_password("password123")
        user.save()  # must not raise
        assert not User.objects.filter(email="x@example.com").exists()

    def test_save_with_update_fields_cannot_bypass_username_rule(self, db):
        user = User.objects._create_user("validuser", "x@example.com", "password123")
        user.username = "no spaces allowed"
        user.save(update_fields=["username"])  # must not raise
        user.refresh_from_db()
        assert user.username == "validuser"


class TestSaveHashingHeuristic:
    def test_set_password_then_save_is_not_double_hashed(self, db):
        user = User(username="validuser", email="x@example.com")
        user.set_password("password123")
        user.save()
        user.refresh_from_db()
        assert check_password("password123", user.password)

    def test_direct_save_of_plain_password_is_hashed_byte_exactly(self, db):
        user = User(username="validuser", email="x@example.com", password="Pass word 123")
        user.save()
        user.refresh_from_db()
        assert user.password != "Pass word 123"
        assert check_password("Pass word 123", user.password)

    def test_direct_save_with_trailing_space_password_stores_byte_exactly(self, db):
        user = User(username="validuser", email="x@example.com", password="password ")
        user.save()
        user.refresh_from_db()
        assert check_password("password ", user.password)
        assert not check_password("password", user.password)


class TestLegitimateFlowsNotBroken:
    def test_manager_create_user_still_works_with_valid_data(self, db):
        user = User.objects._create_user("validuser", "x@example.com", "password123")
        user.refresh_from_db()
        assert check_password("password123", user.password)

    def test_manager_create_user_with_invalid_username_is_refused(self, db):
        with pytest.raises(ValidationError):
            User.objects._create_user("bad name!", "x@example.com", "password123")

    def test_manager_create_user_with_invalid_email_is_refused(self, db):
        with pytest.raises(ValidationError):
            User.objects._create_user("validuser", "not-an-email", "password123")
