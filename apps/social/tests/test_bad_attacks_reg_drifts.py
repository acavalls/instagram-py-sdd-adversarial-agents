"""The Bad — attack iteration 1 on change ``regularize-social-drifts``.

Social-domain attacks: follow race translation, literal (escaped) search.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.social.models import Follow
from apps.social.services import ALREADY_FOLLOWING_ERROR, FollowService

pytestmark = pytest.mark.django_db


def make_user(**overrides):
    data = {"username": "alice", "email": "alice@example.com", "password": "sup3r-secret-pw"}
    data.update(overrides)
    return User.objects.create_user(**data)


class TestFollowRace:
    def test_atk_r015_sequential_duplicate_follow_rejected_with_reference_error(self):
        alice = make_user()
        bob = make_user(username="bob", email="bob@example.com")
        service = FollowService()
        service.follow(alice, bob)
        with pytest.raises(ValidationError) as exc:
            service.follow(alice, bob)
        assert ALREADY_FOLLOWING_ERROR in str(exc.value)
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1

    def test_atk_r016_unfollow_then_immediate_refollow(self):
        alice = make_user()
        bob = make_user(username="bob", email="bob@example.com")
        service = FollowService()
        service.follow(alice, bob)
        service.unfollow(alice, bob)
        follow = service.follow(alice, bob)
        assert follow.pk is not None
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1

    @pytest.mark.django_db(transaction=True)
    def test_atk_r017_race_loser_translated_to_reference_error(self, monkeypatch):
        """Both racers pass ``is_following``; the loser hits the DB unique
        constraint and must receive the reference error, never a 500."""
        alice = make_user()
        bob = make_user(username="bob", email="bob@example.com")
        service = FollowService()

        def fake_is_following(self, follower, following):
            return False  # race window: row exists but the check missed it

        monkeypatch.setattr(FollowService, "is_following", fake_is_following)
        service.follow(alice, bob)  # racer 1 wins
        with pytest.raises(ValidationError) as exc:  # racer 2 hits the constraint
            service.follow(alice, bob)
        assert ALREADY_FOLLOWING_ERROR in str(exc.value)
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1


class TestLiteralSearch:
    def _setup_following(self, user: User) -> None:
        targets = [
            ("user100x", "u100@example.com", ""),
            ("plainbob", "b@example.com", ""),
            ("pctname", "p@example.com", "100%wow"),
            ("underscroll", "u@example.com", "ca_t"),
        ]
        for username, email, first_name in targets:
            followed = make_user(username=username, email=email, first_name=first_name)
            Follow.objects.create(follower=user, following=followed)

    def _followed_usernames(self, user: User, q: str | None) -> list[str]:
        return sorted(u.username for u in FollowService().get_following(user, q=q))

    def test_atk_r018_percent_wildcard_is_literal(self):
        user = make_user()
        self._setup_following(user)
        # '100%' as a wildcard would match 'user100x'; literally it must not
        # (only 'pctname' via its first_name '100%wow').
        assert self._followed_usernames(user, "100%") == ["pctname"]
        # A bare '%' as a literal occurs only in pctname's first_name.
        assert self._followed_usernames(user, "%") == ["pctname"]

    def test_atk_r019_underscore_wildcard_is_literal(self):
        user = make_user()
        self._setup_following(user)
        # '_' as a wildcard would match every 2+ char name; literally it must
        # match only 'underscroll' via its first_name 'ca_t' (usernames are
        # alphanumeric-only, so no username contains '_').
        assert self._followed_usernames(user, "_") == ["underscroll"]

    def test_atk_r020_backslash_ending_query_never_crashes(self):
        user = make_user()
        self._setup_following(user)
        result = self._followed_usernames(user, "\\")
        assert result == []  # no username contains a backslash

    def test_atk_r021_first_name_percent_literal(self):
        user = make_user()
        self._setup_following(user)
        # first_name '100%wow' must match the literal '100%'.
        assert self._followed_usernames(user, "100%") == ["pctname"]
