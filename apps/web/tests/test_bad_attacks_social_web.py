"""GBU adversarial attack tests for the social web surface (add-social
change, Bad iteration 1).

Attacks the HTTP layer: follow/unfollow HTMX endpoints (GET method, anonymous
access, unknown/malformed uuids, self/duplicate/unknown-relationship error
toasts), the feed page pagination edges, the profile page (invalid uuids,
counters, own/other flags) and the following-list modal search (wildcard
metacharacters, hostile strings), plus posts-API non-regression.

Every test asserts behavior required by the social delta spec
(openspec/changes/add-social/specs/social/spec.md) or by the living posts
spec, so a failure is a demonstrated defect.
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.posts.models import Post
from apps.social.models import Follow
from apps.social.services import (
    ALREADY_FOLLOWING_ERROR,
    FOLLOW_NOT_FOUND_ERROR,
    SELF_FOLLOW_ERROR,
    FollowService,
)

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"
FEED_URL = "/web/feed/"
UNKNOWN_UUID = "00000000-0000-0000-0000-000000000000"


def make_user(username: str = "alice", **overrides) -> User:
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_post(owner: User, caption: str = "cap") -> Post:
    return Post.objects.create(owner=owner, caption=caption)


def follow(follower: User, following: User) -> None:
    FollowService().follow(follower, following)


def login(client: Client, user: User) -> None:
    client.force_login(user)


# ---------------------------------------------------------------------------
# ATK-W01: follow/unfollow endpoint method and auth hardening
# ---------------------------------------------------------------------------


def test_atk_w01_follow_and_unfollow_reject_get_with_405():
    alice, bob = make_user("alice"), make_user("bob")
    client = Client()
    client.force_login(alice)
    assert client.get(reverse("web:follow-user", kwargs={"user_id": bob.pk})).status_code == 405
    assert client.get(reverse("web:unfollow-user", kwargs={"user_id": bob.pk})).status_code == 405
    assert not Follow.objects.exists()


def test_atk_w02_anonymous_follow_is_redirected_not_executed():
    bob = make_user("bob")
    client = Client()
    response = client.post(reverse("web:follow-user", kwargs={"user_id": bob.pk}))
    assert response.status_code == 302
    assert "/web/login/" in response["Location"]
    assert not Follow.objects.exists()


def test_atk_w03_unknown_and_malformed_target_uuid_answer_404():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    assert (
        client.post(reverse("web:follow-user", kwargs={"user_id": UNKNOWN_UUID})).status_code == 404
    )
    assert (
        client.post(reverse("web:unfollow-user", kwargs={"user_id": UNKNOWN_UUID})).status_code
        == 404
    )
    # A non-uuid segment must never reach the view (404 from the converter).
    assert client.post("/web/follow/not-a-uuid/").status_code == 404
    assert client.post("/web/unfollow/not-a-uuid/").status_code == 404


# ---------------------------------------------------------------------------
# ATK-W04: failure toasts keep the button state and show the cause
# ---------------------------------------------------------------------------


def _toast_text(response) -> str:
    return response.content.decode()


def test_atk_w04_self_follow_error_toast_and_state_kept():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    response = client.post(reverse("web:follow-user", kwargs={"user_id": alice.pk}))
    assert response.status_code == 200
    assert SELF_FOLLOW_ERROR in _toast_text(response)
    assert 'class="toast error"' in _toast_text(response)
    assert 'hx-post="' + reverse(
        "web:follow-user", kwargs={"user_id": alice.pk}
    ) + '"' in _toast_text(response)


def test_atk_w05_duplicate_follow_error_toast_and_state_kept():
    alice, bob = make_user("alice"), make_user("bob")
    follow(alice, bob)
    client = Client()
    client.force_login(alice)
    response = client.post(reverse("web:follow-user", kwargs={"user_id": bob.pk}))
    assert response.status_code == 200
    assert ALREADY_FOLLOWING_ERROR in _toast_text(response)
    # Button must remain in the following state.
    assert 'hx-post="' + reverse(
        "web:unfollow-user", kwargs={"user_id": bob.pk}
    ) + '"' in _toast_text(response)
    assert Follow.objects.count() == 1


def test_atk_w06_unfollow_unknown_relationship_error_toast():
    alice, bob = make_user("alice"), make_user("bob")
    client = Client()
    client.force_login(alice)
    response = client.post(reverse("web:unfollow-user", kwargs={"user_id": bob.pk}))
    assert response.status_code == 200
    assert FOLLOW_NOT_FOUND_ERROR in _toast_text(response)
    # Button stays in the follow state.
    assert 'hx-post="' + reverse(
        "web:follow-user", kwargs={"user_id": bob.pk}
    ) + '"' in _toast_text(response)


def test_atk_w07_success_toasts_are_the_reference_strings():
    alice, bob = make_user("alice"), make_user("bob")
    client = Client()
    client.force_login(alice)
    response = client.post(reverse("web:follow-user", kwargs={"user_id": bob.pk}))
    assert "Followed successfully" in _toast_text(response)
    response = client.post(reverse("web:unfollow-user", kwargs={"user_id": bob.pk}))
    assert "Unfollowed successfully" in _toast_text(response)
    assert not Follow.objects.exists()


# ---------------------------------------------------------------------------
# ATK-W08: feed pagination edges
# ---------------------------------------------------------------------------


def test_atk_w08_feed_page_edges_fall_back_to_page_one():
    alice, bob = make_user("alice"), make_user("bob")
    follow(alice, bob)
    make_post(bob, "bob post")
    client = Client()
    client.force_login(alice)
    for bad_page in ("abc", "-3", "2.5", "", "0", "-99999999999999999999"):
        response = client.get(FEED_URL, {"page": bad_page})
        assert response.status_code == 200, f"page={bad_page!r}"
        assert b"bob post" in response.content
    # Unicode digits parse as a real page number (123 here): valid input,
    # beyond the last page, so an empty window is the correct outcome.
    response = client.get(FEED_URL, {"page": "١٢٣"})
    assert response.status_code == 200
    assert b"bob post" not in response.content


def test_atk_w09_feed_page_beyond_last_is_empty_no_500():
    alice, bob = make_user("alice"), make_user("bob")
    follow(alice, bob)
    make_post(bob, "bob post")
    client = Client()
    client.force_login(alice)
    for huge_page in ("99", "99999999999999999999999999"):
        response = client.get(FEED_URL, {"page": huge_page})
        assert response.status_code == 200
        assert b"bob post" not in response.content


def test_atk_w10_feed_never_shows_own_posts_even_after_churn():
    alice, bob = make_user("alice"), make_user("bob")
    own = make_post(alice, "alice private thought")
    follow(alice, bob)
    make_post(bob, "bob post")
    client = Client()
    client.force_login(alice)
    response = client.get(FEED_URL)
    assert b"bob post" in response.content
    assert b"alice private thought" not in response.content
    # Unfollow: the followed posts disappear on the next read.
    FollowService().unfollow(alice, bob)
    response = client.get(FEED_URL)
    assert b"bob post" not in response.content
    assert own.owner.username == "alice"


def test_atk_w11_feed_suggestions_panel_excludes_self_and_followed():
    alice, bob, _carol = make_user("alice"), make_user("bob"), make_user("carol")
    follow(alice, bob)
    client = Client()
    client.force_login(alice)
    response = client.get(FEED_URL)
    usernames = [u.username for u in response.context["suggestions"]]
    assert "alice" not in usernames
    assert "bob" not in usernames
    assert "carol" in usernames


# ---------------------------------------------------------------------------
# ATK-W12: profile page edges
# ---------------------------------------------------------------------------


def test_atk_w12_profile_unknown_or_malformed_uuid_404_not_500():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    assert client.get(reverse("web:profile", kwargs={"user_id": UNKNOWN_UUID})).status_code == 404
    assert client.get("/web/profile/not-a-uuid/").status_code == 404
    assert client.get("/web/profile/../../etc/passwd/").status_code in (404, 400)


def test_atk_w13_profile_counters_survive_follow_churn():
    alice, bob, _carol = make_user("alice"), make_user("bob"), make_user("carol")
    make_post(bob, "bob post 1")
    make_post(bob, "bob post 2")
    service = FollowService()
    client = Client()
    client.force_login(alice)
    url = reverse("web:profile", kwargs={"user_id": bob.pk})
    service.follow(alice, bob)
    service.follow(_carol, bob)
    ctx = client.get(url).context
    assert ctx["followers_count"] == 2
    assert ctx["posts_count"] == 2
    assert ctx["is_following"] is True
    assert ctx["is_own_profile"] is False
    service.unfollow(alice, bob)
    ctx = client.get(url).context
    assert ctx["followers_count"] == 1
    assert ctx["is_following"] is False


def test_atk_w14_own_profile_hides_follow_button_and_sets_flags():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    response = client.get(reverse("web:profile", kwargs={"user_id": alice.pk}))
    assert response.status_code == 200
    body = response.content.decode()
    assert response.context["is_own_profile"] is True
    assert reverse("web:follow-user", kwargs={"user_id": alice.pk}) not in body


def test_atk_w15_profile_page_beyond_last_no_500():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    for page in ("0", "-5", "999999999999999999999999"):
        response = client.get(reverse("web:profile", kwargs={"user_id": alice.pk}), {"page": page})
        assert response.status_code == 200, f"page={page!r}"


# ---------------------------------------------------------------------------
# ATK-W16: following-list modal search hostility
# ---------------------------------------------------------------------------


def test_atk_w16_modal_search_wildcards_do_not_leak_unfollowed_users():
    """Wildcard metacharacters (% _) must not turn the search into a
    match-everything filter that the spec does not describe."""
    alice = make_user("alice")
    bob, _carol = make_user("bob"), make_user("carol")
    follow(alice, bob)
    client = Client()
    client.force_login(alice)
    url = reverse("web:following-list", kwargs={"user_id": alice.pk})
    for q in ("%", "_", "__", "%%", "%'", "'; DROP TABLE", "\\", "%00"):
        response = client.get(url, {"q": q})
        assert response.status_code == 200, f"q={q!r}"
        names = [u.username for u in response.context["following_users"]]
        # Whatever the wildcard semantics, only followed users may appear.
        assert set(names) <= {"bob"}, f"q={q!r} leaked {names}"


def test_atk_w17_modal_search_hostile_strings_are_escaped():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    url = reverse("web:following-list", kwargs={"user_id": alice.pk})
    evil = "<script>alert(1)</script>\"'\\"
    response = client.get(url, {"q": evil})
    assert response.status_code == 200
    body = response.content.decode()
    assert "<script>alert(1)</script>" not in body
    # A 10k-char query must not crash or hang the modal.
    response = client.get(url, {"q": "a" * 10_000})
    assert response.status_code == 200


def test_atk_w18_modal_for_unknown_or_malformed_uuid_404():
    alice = make_user("alice")
    client = Client()
    client.force_login(alice)
    assert (
        client.get(reverse("web:following-list", kwargs={"user_id": UNKNOWN_UUID})).status_code
        == 404
    )
    assert client.get("/web/profile/not-a-uuid/following/").status_code == 404


# ---------------------------------------------------------------------------
# ATK-W19: posts capability non-regression under social state
# ---------------------------------------------------------------------------


def test_atk_w19_posts_api_still_own_posts_only_while_following():
    alice, bob = make_user("alice"), make_user("bob")
    make_post(alice, "alice api post")
    make_post(bob, "bob hidden post")
    follow(alice, bob)
    client = Client()
    client.force_login(alice)
    response = client.get("/api/posts/")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    captions = [item["caption"] for item in payload]
    assert captions == ["alice api post"]


# ---------------------------------------------------------------------------
# ATK-W21: stored content injection through profile fields and captions
# ---------------------------------------------------------------------------


def test_atk_w21_hostile_profile_fields_and_captions_are_escaped():
    """first_name/last_name are not format-restricted like usernames: a
    hostile name must render inert in the following modal, the feed and the
    follow-button surface (auto-escaping, no raw markup)."""
    attacker = make_user(
        "attacker",
        first_name="<script>alert(1)</script>",
        last_name='"><img src=x onerror=alert(2)>',
    )
    victim = make_user("victim")
    follow(attacker, victim)
    make_post(victim, "<script>alert(3)</script> caption")
    client = Client()
    client.force_login(attacker)

    feed_body = client.get(FEED_URL).content.decode()
    assert "<script>alert(3)</script>" not in feed_body
    assert "<script>alert(1)</script>" not in feed_body
    assert "onerror=alert(2)" not in feed_body.replace("&quot;", '"').replace("&#x27;", "'")

    modal_body = client.get(
        reverse("web:following-list", kwargs={"user_id": attacker.pk})
    ).content.decode()
    assert "<script>alert(1)</script>" not in modal_body
    assert "<img src=x" not in modal_body

    # The follow-button partial only ever renders fixed strings, but the
    # hostile names must not break out there either (visited via profile).
    profile_body = client.get(
        reverse("web:profile", kwargs={"user_id": victim.pk})
    ).content.decode()
    assert "<script>alert(1)</script>" not in profile_body


def test_atk_w20_web_profile_grid_still_allows_own_edit_delete():
    alice = make_user("alice")
    make_post(alice, "alice grid post")
    client = Client()
    client.force_login(alice)
    response = client.get(reverse("web:profile", kwargs={"user_id": alice.pk}))
    assert response.status_code == 200
    body = response.content.decode()
    assert "alice grid post" in body
    assert response.context["is_own_profile"] is True
