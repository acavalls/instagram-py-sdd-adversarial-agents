"""Bad-agent adversarial attacks on the Story expiry invariant.

Attack surface: the model save path and the raw queryset paths the spec
pins the 24-hour lifetime to (stories: "Story data model" — "an explicitly
provided expiration timestamp that differs from created_at plus exactly 24
hours MUST be rejected with a validation error").
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story
from apps.posts.services import StoryService

ERROR_STORY_EXPIRY_MISMATCH = "Story expiry must be exactly created_at plus 24 hours"


class StoryExpiryInvariantAttacks(TestCase):
    """Try to smuggle stories whose lifetime is not exactly 24 hours."""

    def _make_user(self, username: str) -> User:
        return User.objects._create_user(username, f"{username}@example.com", "password123")

    def _create_story(self, owner: User) -> Story:
        output = StoryService().create(owner=owner)
        assert output.success and output.story is not None
        return output.story

    def test_bad_attack_story_resave_with_tampered_expiry_rejected(self) -> None:
        """Re-saving an existing story with a shifted expires_at must be refused."""
        story = self._create_story(self._make_user("alice"))
        story.expires_at = story.expires_at + timedelta(hours=24)
        with self.assertRaisesMessage(ValidationError, ERROR_STORY_EXPIRY_MISMATCH):
            story.save()

    def test_bad_attack_story_resave_with_past_expiry_rejected(self) -> None:
        """Forcing an existing story to look already-expired via save() must be refused."""
        story = self._create_story(self._make_user("alice"))
        story.expires_at = timezone.now() - timedelta(seconds=1)
        with self.assertRaisesMessage(ValidationError, ERROR_STORY_EXPIRY_MISMATCH):
            story.save()

    def test_bad_attack_story_resave_unchanged_succeeds(self) -> None:
        """A plain re-save of an untouched story keeps the exact 24h lifetime."""
        story = self._create_story(self._make_user("alice"))
        story.save()  # full clean round trip through the DB first
        story.refresh_from_db()
        story.save()
        story.refresh_from_db()
        self.assertEqual(story.expires_at - story.created_at, timedelta(hours=24))

    def test_bad_attack_story_expiry_off_by_one_second_rejected(self) -> None:
        """Expiry off the exact 24h mark by one second must be rejected (both sides)."""
        owner = self._make_user("alice")
        created_at = timezone.now().replace(microsecond=0)
        for delta in (timedelta(hours=24) - timedelta(seconds=1), timedelta(hours=24, seconds=1)):
            story = Story(
                owner=owner,
                created_at=created_at,
                expires_at=created_at + delta,
            )
            with self.assertRaisesMessage(ValidationError, ERROR_STORY_EXPIRY_MISMATCH):
                story.save()
        # The exact mark is the only accepted value.
        exact = Story(
            owner=owner, created_at=created_at, expires_at=created_at + timedelta(hours=24)
        )
        exact.save()
        self.assertEqual(exact.expires_at - exact.created_at, timedelta(hours=24))

    def test_bad_attack_story_lifetime_is_absolute_24_hours(self) -> None:
        """The stored lifetime is exactly 24h of real time regardless of save timing."""
        owner = self._make_user("alice")
        story = self._create_story(owner)
        story.refresh_from_db()
        self.assertEqual(story.expires_at - story.created_at, timedelta(hours=24))

    def test_bad_attack_story_queryset_update_bypasses_save_invariant(self) -> None:
        """Documented ORM-level bypass: queryset.update() skips save() entirely.

        The spec pins the 24-hour rule to the save path, and no web surface
        reaches queryset.update(); this test pins that the bypass is
        ORM-only (the tampered story is correctly treated as expired
        everywhere: inactive, purgeable, invisible in the bar).
        """
        owner = self._make_user("alice")
        story = self._create_story(owner)
        Story.objects.filter(pk=story.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        story.refresh_from_db()
        # The tampered story is not active anywhere...
        self.assertFalse(Story.objects.filter(pk=story.pk).active().exists())
        # ...and the purge removes it together with its views.
        from apps.posts.models import StoryView

        StoryView.objects.create(story=story, viewer=owner)
        deleted = StoryService().cleanup_expired()
        self.assertEqual(deleted, 1)
        self.assertFalse(StoryView.objects.filter(story_id=story.pk).exists())

    def test_bad_attack_story_bulk_create_bypasses_save_invariant(self) -> None:
        """Documented ORM-level bypass: bulk_create skips save() and its validation.

        No web surface reaches bulk_create(); the spec scopes the 24-hour
        rule to the save path. This test pins the current behavior so any
        future web-reachable bulk path cannot silently inherit the hole.
        """
        owner = self._make_user("alice")
        now = timezone.now()
        long_lived = Story(
            owner=owner,
            created_at=now,
            expires_at=now + timedelta(days=365),
        )
        Story.objects.bulk_create([long_lived])
        smuggled = Story.objects.get(pk=long_lived.pk)
        self.assertEqual(smuggled.expires_at - smuggled.created_at, timedelta(days=365))

    def test_bad_attack_story_expiry_boundary_exact_now(self) -> None:
        """Boundary exactness: expires_at == now is expired; one second later is not.

        Both boundary stories are written through the queryset.update()
        bypass (the save path already pins the exact 24h value in
        test_bad_attack_story_expiry_off_by_one_second_rejected); this
        test attacks the *active/purge* boundary used everywhere else.
        """
        owner = self._make_user("alice")
        now = timezone.now()
        exact = Story(owner=owner, created_at=now - timedelta(hours=24), expires_at=now)
        later = Story(
            owner=owner,
            created_at=now - timedelta(hours=24),
            expires_at=now + timedelta(seconds=1),
        )
        Story.objects.bulk_create([exact, later])  # bypass: raw boundary fixtures
        active_ids = set(Story.objects.active().values_list("pk", flat=True))
        self.assertNotIn(exact.pk, active_ids)
        self.assertIn(later.pk, active_ids)
        # Purge removes only the exactly-expired one.
        deleted = StoryService().cleanup_expired()
        self.assertEqual(deleted, 1)
        self.assertTrue(Story.objects.filter(pk=later.pk).exists())
