"""Bad attack (GBU): username rule bypasses and thread-local gate leaks."""

import pytest
from django.core.exceptions import ValidationError
from django.db.models import F, Value

from apps.accounts.models import User


@pytest.mark.django_db
class TestDirectSaveStoragePath:
    """Spec: the username rule MUST hold on every storage path."""

    def test_direct_save_cannot_store_non_alphanumeric_username(self):
        user = User(username="bad!name", email="bypass@x.com")
        user.set_password("password123")
        user.save()
        assert not User.objects.filter(email="bypass@x.com").exists()

    def test_direct_save_cannot_store_short_username(self):
        user = User(username="ab", email="short@x.com")
        user.set_password("password123")
        user.save()
        assert not User.objects.filter(email="short@x.com").exists()

    def test_mutated_instance_save_cannot_store_invalid_username(self):
        user = User.objects.create(username="goodname", email="mut@x.com", password="password123")
        user.username = "now!bad"
        user.save()
        user.refresh_from_db()
        assert user.username == "goodname"


@pytest.mark.django_db
class TestThreadLocalGateNoLeak:
    """The bulk-write gate must not leak past failures or successes."""

    def test_gate_closed_after_failed_bulk_update(self):
        User.objects.create(username="gateuser", email="gate@x.com", password="password123")
        obj = User.objects.get(username="gateuser")
        obj.username = "bad!name"
        with pytest.raises(ValidationError):
            User.objects.bulk_update([obj], ["username"])
        # The internal gate must be off now: expressions still refused.
        with pytest.raises(ValidationError):
            User.objects.update(username=F("username"))

    def test_gate_closed_after_successful_bulk_update(self):
        user = User.objects.create(username="gateok", email="gateok@x.com", password="password123")
        user.username = "gateok2"
        User.objects.bulk_update([user], ["username"])
        with pytest.raises(ValidationError):
            User.objects.update(username=Value("bad!name"))

    def test_bulk_update_refuses_username_mutated_after_construction(self):
        user = User.objects.create(username="mutated1", email="mut2@x.com", password="password123")
        user.username = "mutated!"
        with pytest.raises(ValidationError):
            User.objects.bulk_update([user], ["username"])

    def test_update_with_other_fields_refuses_bad_username(self):
        User.objects.create(username="combined", email="comb@x.com", password="password123")
        with pytest.raises(ValidationError):
            User.objects.update(bio="hello", username="bad!name")

    def test_update_with_other_fields_applies_good_username(self):
        user = User.objects.create(
            username="combined2", email="comb2@x.com", password="password123"
        )
        user.username = "combined3"
        User.objects.bulk_update([user], ["username", "bio"])
        user.refresh_from_db()
        assert user.username == "combined3"
        assert user.bio == ""
