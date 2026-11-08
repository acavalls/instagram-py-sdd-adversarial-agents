"""Expired-story cleanup management command
(stories: "Expired story cleanup" — "Management command cleanup").
"""

import io
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService


class CleanupExpiredStoriesCommandTests(TestCase):
    def test_management_command_cleanup(self) -> None:
        owner = User.objects.create(username="alice", email="alice@example.com", password="x")
        viewer = User.objects.create(username="bob", email="bob@example.com", password="x")
        expired_output = StoryService().create(owner=owner)
        assert expired_output.story is not None
        expired = expired_output.story
        StoryView.objects.create(story=expired, viewer=viewer)
        active_output = StoryService().create(owner=owner)
        assert active_output.story is not None
        active = active_output.story
        Story.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(Story.objects.count(), 2)
        self.assertEqual(StoryView.objects.count(), 1)
        stdout = io.StringIO()

        try:
            call_command("cleanup_expired_stories", stdout=stdout)
        finally:
            for story in Story.objects.all():
                story.image.delete(save=False)

        self.assertIn("Deleted 1 expired stories.", stdout.getvalue())
        self.assertFalse(Story.objects.filter(pk=expired.pk).exists())
        self.assertTrue(Story.objects.filter(pk=active.pk).exists())
        self.assertEqual(StoryView.objects.count(), 0)

    def test_management_command_reports_zero_when_nothing_expired(self) -> None:
        owner = User.objects.create(username="carol", email="carol@example.com", password="x")
        created = StoryService().create(owner=owner)
        assert created.story is not None
        stdout = io.StringIO()

        try:
            call_command("cleanup_expired_stories", stdout=stdout)
        finally:
            for story in Story.objects.all():
                story.image.delete(save=False)

        self.assertIn("Deleted 0 expired stories.", stdout.getvalue())
        self.assertEqual(Story.objects.count(), 1)
