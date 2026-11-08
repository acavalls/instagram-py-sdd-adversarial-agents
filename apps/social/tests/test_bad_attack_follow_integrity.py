"""Bad attack (GBU): follow-relationship integrity under races and cycles.

Attacks the social capability's data invariants ("Follow relationship
data"): duplicate-pair uniqueness and the self-follow ban under racing
submissions, unfollow races, follow/unfollow cycles and the consistency
of `is_following` after failed actions.
"""

import threading
import time

import pytest
from django.db import OperationalError, connections
from django.db.utils import IntegrityError

from apps.accounts.models import User
from apps.social.models import Follow
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

LOCK_ERRORS = ("database is locked", "database table is locked")


def _with_lock_retry(fn, attempts: int = 12):
    """Run `fn`, retrying only SQLite shared-cache lock artifacts.

    The in-memory shared-cache test database rejects a second concurrent
    writer with an immediate table lock; that is a sandbox artifact, not
    an application failure. A real server database would block or hand
    out an IntegrityError instead. Retries wait for the winner's commit.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except OperationalError as exc:
            if not any(token in str(exc).lower() for token in LOCK_ERRORS):
                raise
            time.sleep(0.05 * (attempt + 1))
    return fn()


def _make_user(username: str) -> User:
    return User.objects.create(
        username=username, email=f"{username}@example.com", password="password123"
    )


def _run_concurrently(targets, workers: int = 2) -> list:
    """Run `workers` callables past a start barrier, collecting outcomes.

    The sandbox's in-memory shared-cache SQLite rejects a second
    concurrent writer with an immediate `database table is locked`
    (SQLITE_LOCKED, which ignores busy timeouts). That is a sandbox
    artifact, not an application failure: the tests skip when it happens
    and assert the full invariant on any backend that allows concurrent
    writers (e.g. PostgreSQL).
    """
    barrier = threading.Barrier(workers)
    results: list = []
    lock = threading.Lock()

    def worker(target) -> None:
        try:
            barrier.wait(timeout=10)
            try:
                outcome = _with_lock_retry(target)
            except OperationalError as exc:
                outcome = exc
        except Exception as exc:  # noqa: BLE001 - the outcome IS the result
            outcome = exc
        finally:
            connections.close_all()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(t,)) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def _skip_if_sandbox_locked(results: list) -> None:
    if any(isinstance(result, OperationalError) for result in results):
        pytest.skip(
            "sandbox shared-cache SQLite cannot host two concurrent writers "
            "(SQLITE_LOCKED); invariant still asserted on concurrent-writer backends"
        )


class TestBadAttackConcurrentDuplicateFollow:
    def test_bad_attack_racing_duplicate_follow_yields_one_row(self) -> None:
        """Two racing follows of the same pair must end with a single row
        and one rejection ("Already following this user")."""
        alice = _make_user("racealice")
        bob = _make_user("racebob")
        service = FollowService()

        results = _run_concurrently(
            [
                lambda: service.follow(follower=alice, following=bob),
                lambda: service.follow(follower=alice, following=bob),
            ]
        )

        _skip_if_sandbox_locked(results)
        assert len(results) == 2
        successes = [r for r in results if getattr(r, "success", False)]
        failures = [
            r for r in results if isinstance(r, object) and not getattr(r, "success", False)
        ]
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert exceptions == [], f"unexpected exceptions: {exceptions!r}"
        assert len(successes) == 1, f"expected exactly one success, got {results!r}"
        assert len(failures) == 1
        assert failures[0].error == "Already following this user"  # type: ignore[attr-defined]
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1

    def test_bad_attack_racing_unfollows_leave_no_rows(self) -> None:
        """Two racing unfollows of the same pair: exactly one succeeds,
        the other reports the unknown-relationship cause, no rows remain."""
        alice = _make_user("raceunfalice")
        bob = _make_user("raceunfbob")
        Follow.objects.create(follower=alice, following=bob)
        service = FollowService()

        results = _run_concurrently(
            [
                lambda: service.unfollow(follower=alice, following=bob),
                lambda: service.unfollow(follower=alice, following=bob),
            ]
        )

        _skip_if_sandbox_locked(results)
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert exceptions == [], f"unexpected exceptions: {exceptions!r}"
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 1, f"expected exactly one success, got {results!r}"
        assert len(failures) == 1
        assert failures[0].error == "Follow relationship not found"
        assert not Follow.objects.filter(follower=alice, following=bob).exists()


class TestBadAttackFollowCyclesAndConsistency:
    def test_bad_attack_follow_unfollow_follow_cycle(self) -> None:
        """A full follow/unfollow/refollow cycle ends followed with a
        single row and no stale state."""
        alice = _make_user("cyclealice")
        bob = _make_user("cyclebob")
        service = FollowService()

        assert service.follow(follower=alice, following=bob).success
        assert service.unfollow(follower=alice, following=bob).success
        assert not service.is_following(alice, bob)
        output = service.follow(follower=alice, following=bob)

        assert output.success
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1
        assert service.is_following(alice, bob)

    def test_bad_attack_self_follow_rejected_at_model_level(self) -> None:
        """Even bypassing the service (raw model insert), the database
        check constraint bans the self-pair."""
        solo = _make_user("solo")
        with pytest.raises(IntegrityError):
            Follow.objects.create(follower=solo, following=solo)

    def test_bad_attack_is_following_consistent_after_failed_actions(self) -> None:
        """Failed follow attempts (self, duplicate) never alter the real
        relationship state."""
        alice = _make_user("consalice")
        bob = _make_user("consbob")
        service = FollowService()

        assert not service.follow(follower=alice, following=alice).success
        assert not service.is_following(alice, alice)

        assert service.follow(follower=alice, following=bob).success
        before = service.is_following(alice, bob)
        duplicate = service.follow(follower=alice, following=bob)
        assert not duplicate.success
        assert duplicate.error == "Already following this user"
        assert service.is_following(alice, bob) == before
        assert Follow.objects.filter(follower=alice, following=bob).count() == 1

        # Failed unfollow (unknown relationship) keeps the real state.
        carol = _make_user("conscarol")
        missing = service.unfollow(follower=alice, following=carol)
        assert not missing.success
        assert missing.error == "Follow relationship not found"
        assert service.is_following(alice, bob)
        assert not service.is_following(alice, carol)
