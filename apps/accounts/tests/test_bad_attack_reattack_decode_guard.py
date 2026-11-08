"""Bad re-attack (iteration 3) on the BUG-001 fix in User._password_needs_hashing.

The fix requires identify_hasher(value) AND hasher.decode(value) to succeed
before treating a password as already-hashed. Hypothesis: that guard is still
weaker than a true round-trip (check_password(p, p)); any raw password whose
string shape decodes as a valid hash of its own algorithm (e.g.
"md5$<salt>$<32 hex chars>" with the MD5 hasher installed) passes identify +
decode, is stored VERBATIM on every storage path, and can never authenticate.
"""

import pytest
from django.contrib.auth.hashers import check_password, make_password

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

# Fully decodable md5-shaped lookalike: salt "realsalt", 32 hex chars.
MD5_DECODEABLE = "md5$realsalt$0123456789abcdef0123456789abcdef"


class TestDecodeGuardSurvivorLookalike:
    def test_bulk_create_stores_decodeable_md5_lookalike_raw(self):
        user = User(username="decguard1", email="decguard1@example.com")
        user.password = MD5_DECODEABLE
        User.objects.bulk_create([user])

        stored = User.objects.get(username="decguard1").password
        assert stored != MD5_DECODEABLE, (
            f"BUG: decodeable md5-shaped RAW password stored verbatim "
            f"(and would never authenticate): {stored!r}"
        )
        assert check_password(MD5_DECODEABLE, stored)

    def test_save_stores_decodeable_md5_lookalike_raw(self):
        user = User(username="decguard2", email="decguard2@example.com")
        user.password = MD5_DECODEABLE
        user.save()

        stored = User.objects.get(username="decguard2").password
        assert stored != MD5_DECODEABLE, (
            f"BUG: decodeable md5-shaped RAW password stored verbatim via "
            f"save() (and would never authenticate): {stored!r}"
        )
        assert check_password(MD5_DECODEABLE, stored)

    def test_registration_api_accepts_decodeable_md5_lookalike_and_login_works(self, client):
        from django.conf import settings

        response = client.post(
            "/api/auth/register/",
            {
                "username": "decguard3",
                "email": "decguard3@example.com",
                "password": MD5_DECODEABLE,
            },
            content_type="application/json",
        )
        if response.status_code not in (200, 201):
            pytest.skip(
                f"registration API rejects this password shape ({response.status_code}); "
                "not reachable from the API input path"
            )
        login = client.post(
            "/api/auth/login/",
            {"username": "decguard3", "password": MD5_DECODEABLE},
            content_type="application/json",
        )
        assert login.status_code == 200, (
            f"BUG: registered user cannot log in with the chosen password; "
            f"stored={User.objects.get(username='decguard3').password!r} "
            f"hashers={settings.PASSWORD_HASHERS}"
        )

    def test_guard_weaker_than_true_round_trip_documentation(self):
        # Documents the semantic gap: the value passes identify+decode (the
        # fix's "provable round-trip") but check_password(p, p) is False,
        # i.e. it is provably NOT a hash of itself, so it MUST be hashed.
        from django.contrib.auth.hashers import identify_hasher

        hasher = identify_hasher(MD5_DECODEABLE)
        hasher.decode(MD5_DECODEABLE)  # does not raise -> fix's guard passes
        assert not check_password(MD5_DECODEABLE, MD5_DECODEABLE)


class TestFixPositiveControls:
    """The fix must keep working: real hashes pass through unhashed."""

    def test_set_password_then_save_not_double_hashed(self):
        user = User(username="ctlsave", email="ctlsave@example.com")
        user.set_password("control-password-1")
        user.save()
        stored = User.objects.get(username="ctlsave").password
        assert stored.startswith("md5$"), stored
        assert check_password("control-password-1", stored)

    def test_set_password_then_bulk_create_not_double_hashed(self):
        user = User(username="ctlbulk", email="ctlbulk@example.com")
        user.set_password("control-password-2")
        User.objects.bulk_create([user])
        stored = User.objects.get(username="ctlbulk").password
        assert stored.startswith("md5$"), stored
        assert check_password("control-password-2", stored)

    def test_precomputed_hash_via_direct_assignment_authenticates(self):
        # The accounts.0003 bootstrap shape: a make_password()-computed hash
        # assigned straight to instance.password with the trusted-hash
        # marker set (the required pattern for direct hash assignment, since
        # the marker is the only reliable provenance signal), then persisted.
        precomputed = make_password("bob-ig-pass-1")
        user = User(username="ctlpre", email="ctlpre@example.com")
        user.password = precomputed
        user._password_is_hash = True
        User.objects.bulk_create([user])
        stored = User.objects.get(username="ctlpre").password
        assert stored == precomputed, "pre-computed hash was re-hashed"
        assert check_password("bob-ig-pass-1", stored)
