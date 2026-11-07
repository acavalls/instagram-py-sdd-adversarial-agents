"""The Bad — attack iteration 1 on change ``regularize-social-drifts``.

Accounts-domain attacks: bulk-write username-rule bypasses (F-expression),
create_user(None), byte-exact password comparison, POST-only logout.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db.models import F

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {"username": "alice", "email": "alice@example.com", "password": "sup3r-secret-pw"}
    data.update(overrides)
    return User.objects.create_user(**data)


class TestBulkUsernameRule:
    def test_atk_r007_literal_invalid_username_update_rejected(self):
        user = make_user()
        with pytest.raises(ValidationError):
            User.objects.filter(pk=user.pk).update(username="ab!")
        user.refresh_from_db()
        assert user.username == "alice"

    def test_atk_r008_f_expression_update_bypasses_username_rule(self):
        """Spec delta (user-accounts, User account data): 'The username rule
        MUST hold on every storage path, including queryset bulk operations.'
        An F() expression writing a hostile value into ``username`` through
        ``update()`` is a bulk storage path; the rule cannot be validated
        statically on a non-literal value, so the write is refused with the
        model's username error.
        Orchestrator adjudication: the delta scenario requires rejection
        with a validation error; the F() write is refused with the model's
        username error."""
        user = make_user()
        user.first_name = "Jo"  # valid first_name, invalid username (< 3 chars)
        user.save(update_fields=["first_name"])
        with pytest.raises(ValidationError):
            User.objects.filter(pk=user.pk).update(username=F("first_name"))
        user.refresh_from_db()
        assert User.validate_username_format(user.username) is None, (
            f"F() update stored a rule-violating username: {user.username!r}"
        )

    def test_atk_r009_bulk_create_invalid_username_rejected(self):
        with pytest.raises(ValidationError):
            User.objects.bulk_create(
                [User(username="no!", email="x@example.com", password="sup3r-secret-pw")]
            )
        assert not User.objects.filter(username="no!").exists()

    def test_atk_r010_bulk_create_batch_size_valid_usernames_ok(self):
        users = [
            User(username=f"good{i:02d}", email=f"g{i}@example.com", password="sup3r-secret-pw")
            for i in range(3)
        ]
        User.objects.bulk_create(users, batch_size=2)
        assert User.objects.filter(username__startswith="good").count() == 3

    def test_atk_r011_create_user_none_raises_validation_error(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(None)

    def test_atk_r012_create_user_empty_string_returns_detached_instance(self):
        instance = User.objects.create_user("")
        assert User.validate_username_format(instance.username) is not None
        assert not User.objects.filter(username="").exists()


class TestByteExactPasswordAndLogout:
    def test_atk_r013_password_with_spaces_byte_exact(self, api_client):
        """Spec delta (user-accounts): 'Passwords MUST be compared and stored
        byte-exactly, without whitespace trimming or case folding.'"""
        password = "  Sup3rSecret!  "
        resp = api_client.post(
            "/api/auth/register/",
            {
                "username": "spaced",
                "email": "spaced@example.com",
                "password": password,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content

        # Exact bytes authenticate; trimmed/folded variants must not.
        resp = api_client.post(
            "/api/auth/login/", {"username": "spaced", "password": password}, format="json"
        )
        assert resp.status_code == 200, "byte-exact password failed to authenticate"

        resp = api_client.post(
            "/api/auth/login/", {"username": "spaced", "password": password.strip()}, format="json"
        )
        assert resp.status_code == 401, "trimmed password authenticated (trimming leaked in)"

        resp = api_client.post(
            "/api/auth/login/", {"username": "spaced", "password": password.lower()}, format="json"
        )
        assert resp.status_code == 401, "case-folded password authenticated"

    def test_atk_r014_logout_is_post_only_and_session_survives_get(self, client):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="webby", email="webby@example.com", password="sup3r-secret-pw"
        )
        client.force_login(user)

        resp = client.get("/web/logout/")
        assert resp.status_code == 405, "GET logout must answer 405"

        # Session must still be active: a protected page does not redirect to login.
        resp = client.get("/web/feed/")
        assert resp.status_code == 200, "GET logout cleared the session"

        resp = client.post("/web/logout/")
        assert resp.status_code in (302, 200)
        resp = client.get("/web/feed/")
        assert resp.status_code == 302, "POST logout failed to clear the session"
