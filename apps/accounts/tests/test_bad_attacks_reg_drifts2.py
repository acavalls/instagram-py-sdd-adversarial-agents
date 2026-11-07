"""The Bad — attack iteration 2 on change ``regularize-social-drifts``.

Accounts domain, re-verification of BUG-R002 with different angles
(combined F() expressions, None, related-manager querysets) plus a fresh
``bulk_update`` attack not covered in iteration 1.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db.models import F, Value
from django.db.models.functions import Concat

from apps.accounts.models import User
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {"username": "alice", "email": "alice@example.com", "password": "sup3r-secret-pw"}
    data.update(overrides)
    return User.objects.create_user(**data)


class TestR002Reattack:
    def test_atk_r016_combined_expression_update_rejected(self):
        """BUG-R002 re-check, new angle: a Concat(Value(...), F(...))
        expression is not a str; the rule cannot be validated statically,
        so the whole update() must be refused and store nothing."""
        user = make_user()
        user.first_name = "Jo"  # "x" + "Jo" = "xJo": alphanumeric, would PASS the format rule
        user.save(update_fields=["first_name"])
        with pytest.raises(ValidationError):
            User.objects.filter(pk=user.pk).update(username=Concat(Value("x"), F("first_name")))
        user.refresh_from_db()
        assert user.username == "alice", f"stored {user.username!r}"

    def test_atk_r017_none_username_update_rejected(self):
        """BUG-R002 re-check: update(username=None) is a non-literal with no
        text to validate; it must be refused, not stored as NULL (which the
        NOT NULL column or the rule would both forbid)."""
        user = make_user()
        with pytest.raises(ValidationError):
            User.objects.filter(pk=user.pk).update(username=None)
        user.refresh_from_db()
        assert user.username == "alice"

    def test_atk_r017b_no_user_related_manager_queryset_exists(self):
        """NOT_FEASIBLE_IN_SANDBOX: the schema has no related manager whose
        queryset yields User instances (Follow's related names return Follow
        rows), so a related-manager User update() path does not exist. The
        F() refusal on the default manager queryset is covered by r008/r016."""
        alice = make_user()
        bob = User.objects.create_user(
            username="bobby", email="bob@example.com", password="sup3r-secret-pw"
        )
        Follow.objects.create(follower=alice, following=bob)
        # Reverse related managers here yield Follow rows (User-side related
        # manager querysets do not exist in this schema), so there is no User
        # related-manager update() path to attack.
        assert bob.followers.count() == 1  # reverse related name returns Follow rows


class TestNewBulkUpdateAttack:
    def test_atk_r018_bulk_update_username_bypasses_rule(self):
        """Fresh attack (not covered in iteration 1): ``bulk_update`` is a
        queryset bulk storage path and never calls ``save()`` nor runs the
        ``UserQuerySet.update``/``bulk_create`` guards. Delta (user-accounts,
        User account data): 'The username rule MUST hold on every storage
        path, including queryset bulk operations.' A hostile in-memory
        username must not be persistable through it."""
        user = make_user()
        user.username = "bad name!"
        with pytest.raises(ValidationError):
            User.objects.bulk_update([user], ["username"])
        user.refresh_from_db()
        assert user.username == "alice", f"bulk_update stored {user.username!r}"
