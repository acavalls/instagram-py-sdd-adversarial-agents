"""Adversarial attacks (The Bad) against the regularize-user-accounts-drifts change.

Each test documents an attack (ATK-R-00N) targeting the surfaces this change
touched: the alphanumeric username validator + migration 0002, the
trim_whitespace=False password fields, the 401-on-every-login-failure rule,
and the POST-only CSRF-protected logout.

Rules verified here come from the change's delta spec
(openspec/changes/regularize-user-accounts-drifts/specs/user-accounts/spec.md)
and its design decisions 1-4.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import UserService

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
FEED_URL = "/web/feed/"
LOGOUT_URL = "/web/logout/"

VALID = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "sup3r-secret-pw",
}

GENERIC_401 = {"error": "Invalid credentials"}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def web_client() -> Client:
    return Client()


def register(api: APIClient, **overrides):
    data = dict(VALID)
    data.update(overrides)
    return api.post(REGISTER_URL, data, format="json")


def create_ref_user(**overrides) -> User:
    data = dict(VALID)
    data.update(overrides)
    user = User.objects.create_user(
        username=data["username"], email=data["email"], password=data["password"]
    )
    return user


# ---------------------------------------------------------------------------
# Surface 1: username alphanumeric validator + migration 0002
# ---------------------------------------------------------------------------


class TestUsernameValidatorAttacks:
    def test_atk_r_001_unicode_letters_rejected_on_api_register(self, api):
        """ATK-R-001: username with accented unicode letters ('álice') must be
        rejected on the API registration path (only [a-zA-Z0-9] allowed)."""
        response = register(api, username="álice")
        assert response.status_code == 400
        assert "Username must contain only letters and numbers" in str(response.data)
        assert not User.objects.filter(email="alice@example.com").exists()

    def test_atk_r_002_fullwidth_letters_rejected(self, api):
        """ATK-R-002: fullwidth unicode username ('ａｌｉｃｅ') must be rejected."""
        response = register(api, username="ａｌｉｃｅ")
        assert response.status_code == 400
        assert not User.objects.filter(email="alice@example.com").exists()

    def test_atk_r_003_unicode_digits_rejected_and_ascii_digits_accepted(self, api):
        """ATK-R-003: arabic-indic digits ('al١ce') rejected; 'al1ce' accepted."""
        response = register(api, username="al١ce", email="u1@example.com")
        assert response.status_code == 400
        response = register(api, username="al1ce", email="u2@example.com")
        assert response.status_code == 201

    def test_atk_r_004_length_boundaries(self, api):
        """ATK-R-004: 2 chars rejected, 3 accepted, 150 accepted, 151 rejected."""
        assert register(api, username="ab", email="a@example.com").status_code == 400
        assert register(api, username="abc", email="b@example.com").status_code == 201
        assert register(api, username="u" * 150, email="c@example.com").status_code == 201
        assert register(api, username="u" * 151, email="d@example.com").status_code == 400

    def test_atk_r_005_empty_username_rejected(self, api):
        """ATK-R-005: empty username must be rejected with no user created."""
        response = register(api, username="")
        assert response.status_code == 400
        assert not User.objects.filter(email="alice@example.com").exists()

    def test_atk_r_006_shell_create_user_enforces_alphanumeric_rule(self):
        """ATK-R-006 (design decision 1: 'shell and any future creation path
        enforce the spec rule'): User.objects.create_user with a hostile
        username ('bad name!') must NOT persist a user."""
        User.objects.create_user(
            username="bad name!", email="shell@example.com", password="sup3r-secret-pw"
        )
        assert not User.objects.filter(email="shell@example.com").exists()

    def test_atk_r_007_model_full_clean_matches_validate_username_format(self):
        """ATK-R-007: the model field validator and the service-level
        validate_username_format must agree (design decision 1: the model
        enforces the spec rule on every creation path, admin included).
        'alice\\n' must be rejected (RegexValidator '$' also matches before a
        trailing newline) and 'ab' must be rejected (min length 3)."""
        for hostile in ("alice\n", "ab"):
            user = User(
                username=hostile,
                email=f"hostile-{hostile.strip()}@example.com",
                password="sup3r-secret-pw",
            )
            with pytest.raises(ValidationError) as excinfo:
                user.full_clean()
            assert "username" in excinfo.value.message_dict, hostile

    def test_atk_r_016_race_past_duplicate_check_stores_at_most_one(self, monkeypatch):
        """ATK-R-016 (delta scenario 'Concurrent duplicate registration keeps
        data consistent'): two registrations that both pass the explicit
        duplicate check (simulated race window) must store at most one
        account; storage never keeps a duplicate username or email."""
        monkeypatch.setattr(User, "validate_registration", classmethod(lambda cls, **kw: None))
        service = UserService()
        service.create_user(username="racer", email="racer@example.com", password="sup3r-secret-pw")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                service.create_user(
                    username="racer",
                    email="racer@example.com",
                    password="sup3r-secret-pw",
                )
        assert User.objects.filter(username="racer").count() == 1
        assert User.objects.filter(email="racer@example.com").count() == 1


# ---------------------------------------------------------------------------
# Surface 2: trim_whitespace=False on both password fields
# ---------------------------------------------------------------------------


class TestPasswordWhitespaceAttacks:
    def test_atk_r_008_padded_password_registered_and_logged_byte_exact(self, api):
        """ATK-R-008: a password registered with surrounding spaces must only
        authenticate with those exact spaces; the trimmed variant must fail."""
        assert register(api, password="  passw0rd123  ").status_code == 201
        # Byte-exact padding: accepted.
        ok = api.post(
            LOGIN_URL,
            {"username": "alice", "password": "  passw0rd123  "},
            format="json",
        )
        assert ok.status_code == 200
        # Trimmed credential: rejected.
        trimmed = api.post(
            LOGIN_URL, {"username": "alice", "password": "passw0rd123"}, format="json"
        )
        assert trimmed.status_code == 401
        assert trimmed.json() == GENERIC_401

    def test_atk_r_009_padding_injected_on_unpadded_registration_fails(self, api):
        """ATK-R-009: registering without padding, then logging in with
        padding must fail (no silent normalization anywhere)."""
        assert register(api).status_code == 201
        response = api.post(
            LOGIN_URL,
            {"username": "alice", "password": " sup3r-secret-pw "},
            format="json",
        )
        assert response.status_code == 401
        assert response.json() == GENERIC_401

    def test_atk_r_010_tab_and_newline_password_byte_exact(self, api):
        """ATK-R-010: control characters (tab/newline) are part of the
        credential; register and login must agree byte-exactly."""
        password = "\tpassw0rd12\n"
        assert register(api, password=password).status_code == 201
        ok = api.post(LOGIN_URL, {"username": "alice", "password": password}, format="json")
        assert ok.status_code == 200
        bad = api.post(
            LOGIN_URL,
            {"username": "alice", "password": password.strip()},
            format="json",
        )
        assert bad.status_code == 401

    def test_atk_r_011_internal_multiple_spaces_kept(self, api):
        """ATK-R-011: multiple internal spaces are part of the credential on
        both register and login; a single-space variant must fail."""
        password = "pa  ss w0rd1"
        assert register(api, password=password).status_code == 201
        ok = api.post(LOGIN_URL, {"username": "alice", "password": password}, format="json")
        assert ok.status_code == 200
        collapsed = api.post(
            LOGIN_URL,
            {"username": "alice", "password": "pa ss w0rd1"},
            format="json",
        )
        assert collapsed.status_code == 401

    def test_atk_r_012_web_and_api_paths_share_byte_exact_credentials(self, web_client, api):
        """ATK-R-012: register via the web form with a padded password, then
        the SAME bytes must authenticate on BOTH the web login and the API
        login (API-vs-web credential parity)."""
        web_client.post(
            "/web/register/",
            {
                "username": "carol",
                "email": "carol@example.com",
                "password": "  car0l-pass  ",
            },
        )
        assert User.objects.filter(username="carol").exists()
        web_login = web_client.post(
            "/web/login/", {"username": "carol", "password": "  car0l-pass  "}
        )
        assert web_login.status_code == 302  # redirected to the feed
        api_login = api.post(
            LOGIN_URL,
            {"username": "carol", "password": "  car0l-pass  "},
            format="json",
        )
        assert api_login.status_code == 200
        api_trimmed = api.post(
            LOGIN_URL,
            {"username": "carol", "password": "car0l-pass"},
            format="json",
        )
        assert api_trimmed.status_code == 401


# ---------------------------------------------------------------------------
# Surface 3: LoginAPIView answers 401 generic on every failure shape
# ---------------------------------------------------------------------------

FAILURE_SHAPES = [
    ("blank username", {"username": "", "password": "whatever1"}),
    ("blank password", {"username": "alice", "password": ""}),
    ("missing username", {"password": "whatever1"}),
    ("missing password", {"username": "alice"}),
    ("missing both", {}),
    ("empty object json", None),
    ("null username", {"username": None, "password": "whatever1"}),
    ("null password", {"username": "alice", "password": None}),
    ("list username", {"username": ["alice"], "password": "whatever1"}),
    ("dict password", {"username": "alice", "password": {"a": 1}}),
    ("bool username", {"username": True, "password": "whatever1"}),
    ("unknown user", {"username": "nobody-here", "password": "whatever1"}),
    ("wrong password", {"username": "alice", "password": "wrong-pass-123"}),
    (
        "unicode username unknown",
        {"username": "ｕｎｋｎｏｗｎ", "password": "whatever1"},
    ),
]


class TestLoginFailureShapeAttacks:
    @pytest.fixture(autouse=True)
    def _alice(self):
        User.objects.create_user(
            username="alice", email="alice@example.com", password="sup3r-secret-pw"
        )

    @pytest.mark.parametrize("name,payload", FAILURE_SHAPES)
    def test_atk_r_013_every_failure_shape_is_generic_401(self, api, name, payload):
        """ATK-R-013: every malformed/missing/wrong login payload must answer
        EXACTLY 401 with {'error': 'Invalid credentials'} and never leak which
        field failed (delta scenarios 'Failed API login' and 'API login with
        missing fields')."""
        response = api.post(LOGIN_URL, payload, format="json")
        assert response.status_code == 401, f"shape '{name}' -> {response.status_code}"
        assert response.json() == GENERIC_401, f"shape '{name}' leaked: {response.data}"

    def test_atk_r_014_malformed_json_body_is_a_login_failure(self, api):
        """ATK-R-014: an unparseable request body carries no usable
        credentials (blank/missing username AND password) — per the
        requirement 'On any failure ... MUST respond 401 with the generic
        error' it must be a 401, never a 400 detail leak."""
        response = api.post(LOGIN_URL, data="{not json", content_type="application/json")
        assert response.status_code == 401
        assert response.json() == GENERIC_401

    def test_atk_r_015_empty_body_without_content_type_is_generic_401(self, api):
        """ATK-R-015: an empty body (no fields at all) must be a generic 401."""
        response = api.post(LOGIN_URL, data="", content_type="application/json")
        assert response.status_code == 401
        assert response.json() == GENERIC_401


# ---------------------------------------------------------------------------
# Surface 4: POST-only CSRF-protected logout
# ---------------------------------------------------------------------------


class TestLogoutMethodAttacks:
    @pytest.fixture(autouse=True)
    def _alice(self):
        return User.objects.create_user(
            username="alice", email="alice@example.com", password="sup3r-secret-pw"
        )

    def test_atk_r_017_non_post_logout_is_405_and_session_survives(self, client):
        """ATK-R-017: GET/PUT/PATCH/DELETE/HEAD on /web/logout/ must answer
        405 and must NOT clear the session (the user stays logged in)."""
        client.post("/web/login/", {"username": "alice", "password": "sup3r-secret-pw"})
        assert client.get(FEED_URL).status_code == 200
        for method in ("get", "put", "patch", "delete", "head", "options", "trace"):
            response = getattr(client, method)(LOGOUT_URL)
            assert response.status_code == 405, f"{method.upper()} logout not blocked"
        # The session must survive every non-POST attempt.
        assert client.get(FEED_URL).status_code == 200

    def test_atk_r_018_post_logout_without_csrf_token_is_rejected(self):
        """ATK-R-018: with CsrfViewMiddleware active (it is in MIDDLEWARE) a
        real cross-site client POSTing /web/logout/ without a CSRF token must
        get 403 and the session must survive."""
        client = Client(enforce_csrf_checks=True)
        # Obtain a CSRF token the way a real client would: fetch the login
        # form, then submit it with the token (so the login itself succeeds).
        page = client.get("/web/login/")
        token = client.cookies["csrftoken"].value
        assert page.status_code == 200 and token
        client.post(
            "/web/login/",
            {"username": "alice", "password": "sup3r-secret-pw", "csrfmiddlewaretoken": token},
        )
        assert client.get(FEED_URL).status_code == 200  # logged in
        response = client.post(LOGOUT_URL)  # no CSRF token: hostile client
        assert response.status_code == 403
        assert client.get(FEED_URL).status_code == 200  # session survives

    def test_atk_r_019_double_post_logout_and_anonymous_logout(self, client):
        """ATK-R-019: POST logout twice in a row (second one anonymous) and
        anonymous POST logout must never crash; each answers a redirect."""
        client.post("/web/login/", {"username": "alice", "password": "sup3r-secret-pw"})
        first = client.post(LOGOUT_URL)
        assert first.status_code == 302
        second = client.post(LOGOUT_URL)
        assert second.status_code == 302
        third = Client().post(LOGOUT_URL)  # never logged in at all
        assert third.status_code == 302
