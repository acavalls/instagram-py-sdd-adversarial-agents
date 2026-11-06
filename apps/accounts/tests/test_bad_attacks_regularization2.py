"""Adversarial attacks (The Bad), iteration 2 — attacking the FIXES of the
regularize-user-accounts-drifts change, not the original surface.

Iteration 1 found BUG-001 (UserManager.create_user bypass), BUG-002
(malformed JSON login -> 400 instead of 401) and BUG-003 (``$``-anchored
regex, no MinLengthValidator at model level). This file re-attacks those
three fixes with new shapes: hostile-username persistence paths, login
request bodies DRF must parse defensively, and the newline/length edges of
the re-anchored validator.

Rules verified here come from the change's delta spec
(openspec/changes/regularize-user-accounts-drifts/specs/user-accounts/spec.md),
the living spec's username rule (alphanumeric, 3-150 chars) and the change's
design.md (errors-as-values for create_user).
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"

GENERIC_401 = {"error": "Invalid credentials"}

PASSWORD = "sup3r-secret-pw"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def make_ref_user(username: str = "alice", email: str = "alice@example.com") -> User:
    return User.objects.create_user(username=username, email=email, password=PASSWORD)


# ---------------------------------------------------------------------------
# Fix 1 re-attack: UserManager.create_user / save() / create_superuser
# ---------------------------------------------------------------------------


class TestUserManagerFixAttacks:
    def test_atk_r2_001_create_user_hostile_batch_never_persists(self):
        """ATK-R2-001: the create_user fix must hold for the whole hostile
        batch: spaces/punctuation, unicode letters, trailing newline, too
        short. Per the errors-as-values contract none of them may raise and
        none may persist; each returns a detached (never saved) instance."""
        hostile = ["bad name!", "álice", "alice\n", "ab", "al1ce!"]
        for name in hostile:
            email = f"hostile-{abs(hash(name))}@example.com"
            user = User.objects.create_user(username=name, email=email, password=PASSWORD)
            # A detached instance still carries an in-memory UUID pk (field
            # default), so persistence is checked against the DB, not pk.
            assert user._state.adding, f"{name!r}: instance thinks it is saved"
            assert not User.objects.filter(username=name).exists(), name
            assert not User.objects.filter(email=email).exists(), email
        assert User.objects.count() == 0

    def test_atk_r2_002_create_user_hostile_boundaries_never_persists(self):
        """ATK-R2-002: boundary-hostile usernames through create_user: a
        150-char username with one invalid trailing char, unicode digits, a
        151-char all-valid username, and 3 chars with a space inside must all
        be refused (detached, not persisted) without raising; the exact
        valid boundaries 3 and 150 still persist."""
        hostile = [
            "x" * 149 + "!",  # 150 chars, invalid char
            "al١ce",  # arabic-indic digit
            "u" * 151,  # one over the max
            "a b",  # 3 chars, space inside
        ]
        for name in hostile:
            email = f"b-{abs(hash(name))}@example.com"
            user = User.objects.create_user(username=name, email=email, password=PASSWORD)
            assert user._state.adding, f"{name!r}: instance thinks it is saved"
            assert not User.objects.filter(username=name).exists(), name
            assert not User.objects.filter(email=email).exists(), email
        assert User.objects.count() == 0
        # Valid boundaries still persist.
        assert (
            User.objects.create_user(username="abc", email="lo@example.com", password=PASSWORD).pk
            is not None
        )
        assert (
            User.objects.create_user(
                username="u" * 150, email="hi@example.com", password=PASSWORD
            ).pk
            is not None
        )
        assert User.objects.count() == 2

    def test_atk_r2_003_create_superuser_hostile_never_persists(self):
        """ATK-R2-003 (BUG-004 repro): create_superuser must refuse a hostile
        username under the same errors-as-values contract as create_user —
        the UserManager docstring states the contract for BOTH methods
        ('an invalid username neither raises nor persists').

        ACTUAL: Django's ``contrib.auth.models.UserManager.create_superuser``
        calls ``_create_user`` DIRECTLY (bypassing the project's
        ``create_user`` override), reaches ``User.save()`` and RAISES
        ValidationError instead of returning a detached instance. The
        never-persist invariant holds (nothing is stored), but the refusal
        style breaks the documented manager contract and the claimed
        'create_superuser delegates through create_user' mechanism. Fix:
        override ``create_superuser`` in ``apps.accounts.models.UserManager``
        to delegate through ``self.create_user`` (which already returns the
        detached instance)."""
        user = User.objects.create_superuser(
            username="bad name!", email="root@example.com", password=PASSWORD
        )
        assert user._state.adding
        assert not User.objects.filter(email="root@example.com").exists()
        assert User.objects.count() == 0

    def test_atk_r2_004_bare_create_and_save_refuse_hostile_username(self):
        """ATK-R2-004: every save()-based path refuses a hostile username:
        User.objects.create() raises ValidationError without persisting; a
        persisted user whose username is later mutated to a hostile value
        cannot be stored, neither with bare save() nor with
        save(update_fields=['username']) — the stored value stays intact."""
        # create() -> save() -> ValidationError, nothing persisted.
        with pytest.raises(ValidationError):
            User.objects.create(username="bad name!", email="create@example.com", password=PASSWORD)
        assert not User.objects.filter(email="create@example.com").exists()

        user = make_ref_user()
        original = user.username
        user.username = "bad name!"
        with pytest.raises(ValidationError):
            user.save()
        user.refresh_from_db()
        assert user.username == original

        user.username = "bad name!"
        with pytest.raises(ValidationError):
            user.save(update_fields=["username"])
        user.refresh_from_db()
        assert user.username == original
        # The untouched user still saves fine with update_fields.
        user.email = "alice+ok@example.com"
        user.save(update_fields=["email"])

    @pytest.mark.xfail(strict=False, reason="documented bypass (see docstring)")
    def test_atk_r2_005_queryset_update_and_bulk_create_bypass_model_rule(self):
        """ATK-R2-005 (observation, NOT charged as a bug): queryset-level
        writes (.update(), bulk_create()) skip Model.save() and the field
        validators by Django design; the change's stated scope is the
        creation paths (create_user/create_superuser/bare save/forms), not a
        DB-level CHECK constraint. This test asserts the IDEAL (rule holds)
        and is expected to fail (xfail) today; it would xpass if The Good
        later adds a DB-level guard."""
        user = make_ref_user()
        User.objects.filter(pk=user.pk).update(username="bad name!")
        user.refresh_from_db()
        assert user.username != "bad name!"  # fails today -> xfail
        with transaction.atomic():
            User.objects.bulk_create(
                [User(username="bad name!", email="bulk@example.com", password=PASSWORD)]
            )
        assert not User.objects.filter(email="bulk@example.com").exists()  # fails today


# ---------------------------------------------------------------------------
# Fix 2 re-attack: login failure shapes (raw bodies DRF must parse)
# ---------------------------------------------------------------------------

RAW_BODY_SHAPES = [
    ("json array", f'[{{"username": "alice", "password": "{PASSWORD}"}}]'),
    ("json null", "null"),
    ("json string", '"alice"'),
    ("json number", "123"),
    ("json true", "true"),
    ("binary garbage", b"\x00\x01\x02\xff\xfe garbage"),
    ("truncated json", '{"username": "alice", '),
    ("json nan", '{"username": NaN, "password": "x"}'),
    (
        "huge json string body",
        '"' + "x" * (1024 * 1024) + '"',
    ),
    (
        "huge invalid json body",
        '{"username": "' + "x" * (1024 * 1024) + ",",
    ),
]


class TestLoginMalformedBodyAttacks:
    @pytest.fixture(autouse=True)
    def _alice(self):
        make_ref_user()

    @pytest.mark.parametrize("name,body", RAW_BODY_SHAPES)
    def test_atk_r2_006_raw_body_shapes_are_generic_401(self, api, name, body):
        """ATK-R2-006: every raw body shape — JSON array/null/scalars, binary
        garbage, truncated JSON, NaN, huge bodies — must answer EXACTLY 401
        with {'error': 'Invalid credentials'} (never 400/415/500): the
        BUG-002 fix must cover more than the single '{not json' probe."""
        response = api.post(
            LOGIN_URL,
            data=body,
            content_type="application/json",
        )
        assert response.status_code == 401, f"shape '{name}' -> {response.status_code}"
        assert response.json() == GENERIC_401, f"shape '{name}' leaked: {response.data}"

    def test_atk_r2_007_wrong_content_type_json_body(self, api):
        """ATK-R2-007 (conservative probe): a JSON-ish body sent with a
        content type DRF cannot negotiate (text/plain). DRF answers
        415 UnsupportedMediaType, which is NOT mapped by the BUG-002 fix.
        Per the change's conservative reading this is recorded as
        spec-silent: 415 is a request-level content-negotiation rejection
        and the delta spec only mandates 401 for login attempts whose body
        carries fields. Documented, not charged."""
        response = api.post(
            LOGIN_URL,
            data=f'{{"username": "alice", "password": "{PASSWORD}"}}',
            content_type="text/plain",
        )
        assert response.status_code in (401, 415)
        if response.status_code == 415:
            # Spec-silent: acceptable per the conservative reading above;
            # a 401 mapping would also be acceptable.
            pass


# ---------------------------------------------------------------------------
# Fix 3 re-attack: newline/length edges of the re-anchored validator
# ---------------------------------------------------------------------------


class TestUsernameEdgeAttacks:
    def test_atk_r2_008_trailing_whitespace_is_trimmed_consistently(self, api):
        """ATK-R2-008: trailing newline/tab on the API is trimmed by the
        serializer before validation (DRF CharField), the web path strips
        identically, so BOTH paths store the compliant value 'alice' — never
        'alice\\n'. An INTERNAL newline is not trimmed and must be rejected
        on both paths."""
        response = api.post(
            REGISTER_URL,
            {"username": "alice\n", "email": "alice@example.com", "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 201
        assert User.objects.get(email="alice@example.com").username == "alice"

        response = api.post(
            REGISTER_URL,
            {"username": "bob\r", "email": "cr@example.com", "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 201
        assert User.objects.get(email="cr@example.com").username == "bob"

        # Internal newline: not trimmable -> rejected, nothing stored.
        response = api.post(
            REGISTER_URL,
            {"username": "ali\nce", "email": "in@example.com", "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 400
        assert not User.objects.filter(email="in@example.com").exists()

    def test_atk_r2_009_model_full_clean_length_boundaries_and_control_chars(self):
        """ATK-R2-009: at model level (no trimming) the re-anchored validator
        must reject 'ab', a 151-char username and every trailing control
        char (\\n, \\t, \\r, \\r\\n) via full_clean(); the exact boundaries
        3 and 150 must pass."""
        for hostile in ("ab", "u" * 151, "alice\n", "alice\t", "alice\r", "alice\r\n"):
            user = User(
                username=hostile,
                email=f"m-{abs(hash(hostile))}@example.com",
                password=PASSWORD,
            )
            with pytest.raises(ValidationError) as excinfo:
                user.full_clean()
            assert "username" in excinfo.value.message_dict, repr(hostile)
        for ok_name in ("abc", "u" * 150):
            user = User(
                username=ok_name,
                email=f"ok-{len(ok_name)}@example.com",
                password=PASSWORD,
            )
            user.full_clean()  # must not raise
