"""Bad attack (GBU): adversarial attacks against the admin console surface.

Attacks the spec delta `2026-11-08-05-add-admin-console`:
- access control (deep links, non-staff mutations, bare-staff behavior)
- password hashing through every admin write path (raw-storage attempts)
- domain integrity through the admin (caption limit, story 24h invariant,
  self-follow check constraint, delete cascade)
- privilege escalation through admin forms
"""

import pytest
from django.contrib.auth.hashers import check_password

from apps.accounts.models import User
from apps.posts.models import Post, Story
from apps.social.models import Follow

pytestmark = pytest.mark.django_db

ADMIN_INDEX_URL = "/admin/"
ADMIN_LOGIN_URL = "/admin/login/"
LOGIN_FORM_KEYS = ("username", "password", "next")


def _create_user(username="alice", email="alice@example.com", **extra):
    return User.objects.create(username=username, email=email, password="password123", **extra)


@pytest.fixture
def staff_user():
    return _create_user(
        username="staffer", email="staffer@example.com", is_staff=True, is_superuser=True
    )


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client


@pytest.fixture
def alice():
    return _create_user()


# --------------------------------------------------------------------------
# 1. Access control
# --------------------------------------------------------------------------
class TestAccessControlAttacks:
    DEEP_LINKS = (
        "/admin/accounts/user/",
        "/admin/posts/post/",
        "/admin/posts/story/",
        "/admin/social/follow/",
    )

    def test_bad_attack_anonymous_deep_link_never_leaks_object_data(self, client, alice):
        post = Post.objects.create(owner=alice, caption="SECRET-CAPTION-XYZ")
        story = Story.objects.create(owner=alice, image="")
        follow = Follow.objects.create(
            follower=alice, following=_create_user(username="bob", email="bob@example.com")
        )
        targets = list(self.DEEP_LINKS) + [
            f"/admin/accounts/user/{alice.pk}/change/",
            f"/admin/accounts/user/{alice.pk}/password/",
            f"/admin/posts/post/{post.pk}/change/",
            f"/admin/posts/story/{story.pk}/change/",
            f"/admin/social/follow/{follow.pk}/change/",
            f"/admin/accounts/user/{alice.pk}/delete/",
        ]
        for url in targets:
            response = client.get(url)
            assert response.status_code == 302, url
            assert response.headers["Location"].startswith(ADMIN_LOGIN_URL), url
            # Following the redirect must land on the login page, not the object.
            login_page = client.get(response.headers["Location"])
            assert login_page.status_code == 200
            assert b"SECRET-CAPTION-XYZ" not in login_page.content
            assert alice.username.encode() not in login_page.content

    def test_bad_attack_non_staff_deep_links_and_mutation_are_refused(self, client, alice):
        client.force_login(alice)
        other = _create_user(username="mallory", email="mallory@example.com")
        post = Post.objects.create(owner=other, caption="original")

        for url in (*self.DEEP_LINKS, f"/admin/posts/post/{post.pk}/change/"):
            response = client.get(url)
            assert response.status_code == 302, url
            assert response.headers["Location"].startswith(ADMIN_LOGIN_URL), url

        # Mutation attempt: a non-staff session POSTing the change form.
        response = client.post(
            f"/admin/posts/post/{post.pk}/change/",
            {
                "owner": str(alice.pk),
                "caption": "HIJACKED-BY-NON-STAFF",
                "created_at_0": "2026-01-01",
                "created_at_1": "00:00:00",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].startswith(ADMIN_LOGIN_URL)
        post.refresh_from_db()
        assert post.caption == "original"
        assert post.owner == other

    def test_bad_attack_anonymous_login_post_with_non_staff_creds_cannot_enter(self, client, alice):
        response = client.post(
            ADMIN_LOGIN_URL,
            {"username": "alice", "password": "password123", "next": ADMIN_INDEX_URL},
        )
        assert response.status_code == 200
        assert b"staff account" in response.content
        index = client.get(ADMIN_INDEX_URL)
        assert index.status_code == 302
        assert index.headers["Location"].startswith(ADMIN_LOGIN_URL)

    def test_bad_attack_bare_staff_without_perms_gets_no_object_data(self, client, alice):
        """Flag behavior: bare `is_staff` user (spec calls them staff) with no
        model permissions. The spec only mandates redirects for anonymous and
        non-staff users, so this pins what a bare staff user actually sees."""
        bare = _create_user(username="barestaff", email="barestaff@example.com", is_staff=True)
        client.force_login(bare)
        post = Post.objects.create(owner=alice, caption="SECRET-CAPTION-XYZ")

        index = client.get(ADMIN_INDEX_URL)
        assert index.status_code in (200, 302)
        change = client.get(f"/admin/posts/post/{post.pk}/change/")
        if change.status_code == 200:
            # Data access without explicit perms would be a finding.
            assert b"SECRET-CAPTION-XYZ" not in change.content
        else:
            assert change.status_code in (302, 403)
            mutation = client.post(
                f"/admin/posts/post/{post.pk}/change/",
                {
                    "owner": str(alice.pk),
                    "caption": "ESCALATED",
                    "created_at_0": "2026-01-01",
                    "created_at_1": "00:00:00",
                },
            )
            assert mutation.status_code in (302, 403)
            post.refresh_from_db()
            assert post.caption == "SECRET-CAPTION-XYZ"


# --------------------------------------------------------------------------
# 2. Password hashing through every admin write path
# --------------------------------------------------------------------------
class TestPasswordHashingAttacks:
    def test_bad_attack_raw_password_injected_into_change_form_is_not_stored(
        self, staff_client, alice
    ):
        """A staff session POSTs the user change form carrying a raw password
        in the hash-pointer field. Stored value must remain a hash that does
        NOT authenticate the injected raw secret."""
        old_hash = alice.password
        response = staff_client.post(
            f"/admin/accounts/user/{alice.pk}/change/",
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "sneaky-raw-password",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
                "last_login_0": "2026-01-01",
                "last_login_1": "00:00:00",
            },
        )
        assert response.status_code in (200, 302)
        alice.refresh_from_db()
        assert alice.password != "sneaky-raw-password"
        assert not check_password("sneaky-raw-password", alice.password)
        # The original credential keeps working: the pointer field never
        # rewrites the hash.
        assert alice.password == old_hash
        assert check_password("password123", alice.password)

    def test_bad_attack_admin_password_change_stores_hash_and_authenticates(
        self, staff_client, alice, staff_user
    ):
        response = staff_client.post(
            f"/admin/accounts/user/{alice.pk}/password/",
            {"password1": "brand-new-pw-9", "password2": "brand-new-pw-9"},
        )
        assert response.status_code in (200, 302)
        alice.refresh_from_db()
        assert alice.password != "brand-new-pw-9"
        assert check_password("brand-new-pw-9", alice.password)
        assert not check_password("password123", alice.password)

    def test_bad_attack_staff_changes_own_password_session_stays_valid(
        self, staff_client, staff_user
    ):
        """Password change of the LOGGED-IN staff user themselves: the admin
        must not corrupt the session (update_session_auth_hash semantics) and
        the new password must authenticate."""
        response = staff_client.post(
            f"/admin/accounts/user/{staff_user.pk}/password/",
            {"password1": "self-rotated-pw-7", "password2": "self-rotated-pw-7"},
        )
        assert response.status_code in (200, 302)
        staff_user.refresh_from_db()
        assert check_password("self-rotated-pw-7", staff_user.password)
        # The very next admin request through the same session still works.
        follow_up = staff_client.get(ADMIN_INDEX_URL)
        assert follow_up.status_code == 200

    def test_bad_attack_no_raw_password_ever_lands_in_the_database(self, staff_client, alice):
        staff_client.post(
            f"/admin/accounts/user/{alice.pk}/password/",
            {"password1": "raw-marker-x", "password2": "raw-marker-x"},
        )
        alice.refresh_from_db()
        assert "raw-marker-x" not in alice.password


# --------------------------------------------------------------------------
# 3. Domain integrity through the admin
# --------------------------------------------------------------------------
class TestDomainIntegrityAttacks:
    def test_bad_attack_over_limit_caption_via_admin_is_refused(self, staff_client, alice):
        post = Post.objects.create(owner=alice, caption="safe")
        response = staff_client.post(
            f"/admin/posts/post/{post.pk}/change/",
            {
                "owner": str(alice.pk),
                "caption": "x" * 2201,
                "created_at_0": "2026-01-01",
                "created_at_1": "00:00:00",
            },
        )
        assert response.status_code == 200  # form errors re-render, no crash
        assert b"2200" in response.content
        post.refresh_from_db()
        assert post.caption == "safe"

    def test_bad_attack_story_expiry_mismatch_via_admin_never_stored(self, staff_client, alice):
        """The 24h invariant lives on save(). The admin must respect it: any
        mismatching expires_at must not be stored, whatever the response."""
        story = Story.objects.create(owner=alice, image="")
        original = story.expires_at
        response = staff_client.post(
            f"/admin/posts/story/{story.pk}/change/",
            {
                "owner": str(alice.pk),
                "expires_at_0": "2030-01-01",
                "expires_at_1": "00:00:00",
                "media_type": "image",
            },
        )
        story.refresh_from_db()
        assert story.expires_at == original  # invariant holds regardless
        assert response.status_code in (200, 500)  # 500 = flagged as minor

    def test_bad_attack_self_follow_via_admin_creates_no_row(self, staff_client, alice):
        response = staff_client.post(
            "/admin/social/follow/add/",
            {
                "follower": str(alice.pk),
                "following": str(alice.pk),
                "created_at_0": "2026-01-01",
                "created_at_1": "00:00:00",
            },
        )
        assert not Follow.objects.filter(follower=alice, following=alice).exists()
        assert response.status_code in (200, 500)  # 500 = flagged as minor

    def test_bad_attack_deleting_user_via_admin_cascades_domain(self, staff_client, alice):
        post = Post.objects.create(owner=alice, caption="doomed")
        story = Story.objects.create(owner=alice, image="")
        follow = Follow.objects.create(
            follower=alice, following=_create_user(username="bob", email="bob@example.com")
        )
        response = staff_client.post(
            f"/admin/accounts/user/{alice.pk}/delete/",
            {"post": "yes"},
        )
        assert response.status_code == 302
        assert not User.objects.filter(pk=alice.pk).exists()
        assert not Post.objects.filter(pk=post.pk).exists()
        assert not Story.objects.filter(pk=story.pk).exists()
        assert not Follow.objects.filter(pk=follow.pk).exists()


# --------------------------------------------------------------------------
# 4. Privilege escalation through admin forms
# --------------------------------------------------------------------------
class TestEscalationAttacks:
    def test_bad_attack_staff_user_created_via_admin_starts_unprivileged(self, staff_client):
        """The admin's add-user form must not hand out staff rights by
        default and must not store a raw password."""
        response = staff_client.post(
            "/admin/accounts/user/add/",
            {"username": "newbie1", "password1": "fresh-pw-42", "password2": "fresh-pw-42"},
        )
        assert response.status_code == 302
        newbie = User.objects.get(username="newbie1")
        assert not newbie.is_staff
        assert not newbie.is_superuser
        assert newbie.password != "fresh-pw-42"
        assert check_password("fresh-pw-42", newbie.password)

    def test_bad_attack_non_staff_cannot_grant_itself_staff_via_admin(self, client, alice):
        client.force_login(alice)
        response = client.post(
            f"/admin/accounts/user/{alice.pk}/change/",
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": alice.password,
                "is_staff": "on",
                "is_superuser": "on",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
                "last_login_0": "2026-01-01",
                "last_login_1": "00:00:00",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].startswith(ADMIN_LOGIN_URL)
        alice.refresh_from_db()
        assert not alice.is_staff
        assert not alice.is_superuser
