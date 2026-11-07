"""Adversarial attacks (The Bad), iteration 3 — focused re-attack of the
iteration-3 fix ONLY: ``UserManager.create_superuser`` delegating through the
errors-as-values ``create_user``.

Iteration 2 found BUG-004 (contrib ``create_superuser`` called ``_create_user``
directly, raising ValidationError on hostile usernames instead of returning a
detached instance). The fix replicates Django's superuser flag handling
(``setdefault`` for ``is_staff``/``is_superuser``/``is_active``, ``ValueError``
when explicitly falsy) and delegates through ``create_user``. This file
attacks that fix and its interactions:

1. Hostile string usernames through ``create_superuser`` must return a
   detached (``_state.adding`` True), never-persisted instance without
   raising (errors-as-values contract, manager docstring of
   ``apps/accounts/models.py``).
2. Valid superusers keep Django's contract: flags True persisted, explicit
   falsy ``is_staff``/``is_superuser`` raise ``ValueError``, extra fields
   pass through.
3. Interactions: duplicate username, hostile-with-extra-fields, falsy/None
   usernames reaching the delegated ``create_user``.

Rules come from the change's delta spec
(openspec/changes/regularize-user-accounts-drifts/specs/user-accounts/spec.md),
the living spec's username rule (alphanumeric, 3-150 chars) and the manager
docstring's errors-as-values contract for BOTH create_user and
create_superuser.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "sup3r-secret-pw"


def unique_email(tag: str) -> str:
    return f"root-{tag}@example.com"


class TestCreateSuperuserHostileUsernames:
    def test_atk_r3_001_hostile_batch_detached_never_persisted(self):
        """ATK-R3-001: the create_superuser delegation must hold for the whole
        hostile string batch: spaces/punctuation, unicode letters, trailing
        newline, too short, 150 chars with one invalid char, unicode digits.
        Per the errors-as-values contract none of them may raise and none may
        persist; each returns a detached instance."""
        hostile = [
            "bad name!",
            "álice",
            "alice\n",
            "ab",
            "x" * 149 + "!",  # 150 chars, invalid char
            "١٢٣",  # arabic-indic digits
            "root!",  # valid length, invalid char
        ]
        for name in hostile:
            email = unique_email(str(abs(hash(name))))
            user = User.objects.create_superuser(username=name, email=email, password=PASSWORD)
            assert user._state.adding, f"{name!r}: instance thinks it is saved"
            assert not User.objects.filter(username=name).exists(), name
            assert not User.objects.filter(email=email).exists(), email
            # The detached instance still carries the superuser flags the fix
            # sets before delegating.
            assert user.is_staff and user.is_superuser, name
        assert User.objects.count() == 0

    def test_atk_r3_005_hostile_with_extra_fields_and_save_guard(self):
        """ATK-R3-005: a hostile username through create_superuser WITH
        extra_fields returns a detached instance carrying the passthrough
        fields and flags; and the detached instance cannot leak into storage
        later — a direct .save() on it raises ValidationError (the model-level
        guard), leaving the DB empty."""
        user = User.objects.create_superuser(
            username="bad name!",
            email=unique_email("extras"),
            password=PASSWORD,
            bio="hostile extra",
        )
        assert user._state.adding
        assert user.is_staff and user.is_superuser
        assert user.bio == "hostile extra"
        assert user.email == unique_email("extras")
        assert not User.objects.filter(email=unique_email("extras")).exists()
        with pytest.raises(ValidationError):
            user.save()
        assert User.objects.count() == 0


class TestCreateSuperuserValidContract:
    def test_atk_r3_002_valid_superuser_flags_password_email_bio(self):
        """ATK-R3-002: a valid username through create_superuser persists with
        Django's contract intact: is_staff/is_superuser/is_active True, a
        usable password, normalized email, and extra_fields (bio) passed
        through and persisted."""
        user = User.objects.create_superuser(
            username="rootadmin",
            email="RoOt@EXAMPLE.COM",
            password=PASSWORD,
            bio="boss",
        )
        assert not user._state.adding
        assert User.objects.filter(username="rootadmin").exists()
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True
        assert user.check_password(PASSWORD)
        # normalize_email lowercases the DOMAIN only (Django semantics).
        assert user.email == "RoOt@example.com"
        assert user.bio == "boss"

    def test_atk_r3_003_explicit_falsy_flags_raise_valueerror(self):
        """ATK-R3-003: Django's superuser contract is preserved by the fix:
        explicitly falsy is_staff or is_superuser raises ValueError BEFORE any
        persistence; the defaults (not passed) are True."""
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                username="nostaff",
                email=unique_email("nostaff"),
                password=PASSWORD,
                is_staff=False,
            )
        assert not User.objects.filter(email=unique_email("nostaff")).exists()

        with pytest.raises(ValueError):
            User.objects.create_superuser(
                username="nosuper",
                email=unique_email("nosuper"),
                password=PASSWORD,
                is_superuser=False,
            )
        assert not User.objects.filter(email=unique_email("nosuper")).exists()

        with pytest.raises(ValueError):
            User.objects.create_superuser(
                username="nullstaff",
                email=unique_email("nullstaff"),
                password=PASSWORD,
                is_staff=None,
            )
        assert not User.objects.filter(email=unique_email("nullstaff")).exists()
        assert User.objects.count() == 0


class TestCreateSuperuserInteractions:
    def test_atk_r3_004_duplicate_username_matches_create_user_behavior(self):
        """ATK-R3-004 (mandated observation): create_superuser('alice') when
        'alice' already exists. The errors-as-values contract covers username
        FORMAT; duplicates fall through to Django's unique constraint in BOTH
        paths: create_user and create_superuser must behave identically
        (IntegrityError, exactly one row, no second account)."""
        User.objects.create_user(username="alice", email="alice@example.com", password=PASSWORD)
        # atomic() savepoint: the IntegrityError would poison the outer test
        # transaction (sqlite); a savepoint keeps the session queryable.
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create_superuser(
                username="alice", email="root@example.com", password=PASSWORD
            )
        assert User.objects.filter(username="alice").count() == 1
        assert not User.objects.filter(email="root@example.com").exists()

    def test_atk_r3_006_none_username_raises_validation_error(self):
        """ATK-R3-006 (BUG-005, fixed by regularize-social-drifts, task 2.2 —
        design decision 7): create_superuser(None, ...) — and create_user
        (None, ...) through the same delegation — used to crash with an
        unhandled TypeError (``len(None)`` inside
        ``validate_username_format``). The manager now raises the model's
        username validation error (ValidationError carrying the length-rule
        message) and persists nothing; it never TypeErrors."""
        with pytest.raises(ValidationError):
            User.objects.create_superuser(
                username=None,  # type: ignore[arg-type]  # BUG-005 repro: None is the attack
                email=unique_email("none"),
                password=PASSWORD,
            )
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username=None,  # type: ignore[arg-type]  # BUG-005 repro: None is the attack
                email=unique_email("none-user"),
                password=PASSWORD,
            )
        assert not User.objects.filter(email=unique_email("none")).exists()
        assert not User.objects.filter(email=unique_email("none-user")).exists()
        assert User.objects.count() == 0
