"""The Bad — attack iteration 1 on change ``regularize-social-drifts``.

Posts-domain attacks: media-count guard bypasses, ordering tiebreaker
stability, ordering independence from ``updated_at``.
"""

from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.posts.models import MEDIA_MAX_COUNT, MEDIA_TOO_MANY_ERROR, Post, PostMedia
from apps.posts.services import PostService
from apps.social.services import FeedService

pytestmark = pytest.mark.django_db

POSTS_URL = "/api/posts/"

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def make_user(**overrides: Any) -> User:
    data = {"username": "alice", "email": "alice@example.com", "password": "sup3r-secret-pw"}
    data.update(overrides)
    return User.objects.create_user(**data)


def make_media_file(name: str = "media.gif"):
    return SimpleUploadedFile(name, GIF_BYTES, content_type="image/gif")


def auth_client(api_client: APIClient, user: User) -> APIClient:
    token = AccessToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


class TestMediaGuardBypasses:
    def test_atk_r001_postmedia_bulk_create_bypasses_count_guard(self):
        """Design decision 3 claims the media-count invariant holds on EVERY
        persistence path. ``PostMedia.objects.bulk_create`` skips
        ``PostMedia.save()`` exactly like ``User`` bulk writes did before
        F-04 was fixed. Spec (posts delta, Post data model): 'up to 10
        ordered files attached to a post'."""
        user = make_user()
        post = Post.objects.create(owner=user, caption="bulk")
        files = [
            PostMedia(post=post, image=make_media_file(f"{i}.gif"), order=i) for i in range(11)
        ]
        PostMedia.objects.bulk_create(files)
        assert PostMedia.objects.filter(post=post).count() == 10, (
            "bulk_create bypassed the 10-media invariant"
        )

    def test_atk_r002_media_guard_update_path_and_readd_after_delete(self):
        """Boundary and mutation paths: exactly 10 accepted, 11th rejected,
        deleting one media allows adding one back, and re-pointing an
        existing media row to a full post is rejected."""
        user = make_user()
        service = PostService()
        post = service.create(user, "cap", [make_media_file(f"{i}.gif") for i in range(10)])
        assert post.media.count() == 10

        # 11th via the save path is rejected
        with pytest.raises(ValidationError) as exc:
            PostMedia(post=post, image=make_media_file("11.gif"), order=10).save()
        assert MEDIA_TOO_MANY_ERROR in str(exc.value)

        # Delete one -> re-adding one must now succeed
        PostMedia.objects.filter(post=post, order=9).first().delete()
        readd = PostMedia(post=post, image=make_media_file("readd.gif"), order=9)
        readd.save()
        assert post.media.count() == 10

        # A second full post; re-pointing readd to it must be rejected
        other = service.create(user, "other", [make_media_file(f"o{i}.gif") for i in range(10)])
        readd.post = other
        with pytest.raises(ValidationError):
            readd.save()

    def test_atk_r003_service_create_boundary_10_ok_11_rejected(self):
        user = make_user()
        service = PostService()
        post = service.create(user, "", [make_media_file() for _ in range(MEDIA_MAX_COUNT)])
        assert post.media.count() == 10
        with pytest.raises(ValidationError) as exc:
            service.create(user, "", [make_media_file() for _ in range(MEDIA_MAX_COUNT + 1)])
        assert MEDIA_TOO_MANY_ERROR in str(exc.value)


class TestOrderingTiebreaker:
    def _same_timestamp_posts(self, user: User, count: int) -> list[Post]:
        stamp = timezone.now()
        posts = [Post.objects.create(owner=user, caption=f"c{i}") for i in range(count)]
        # Force identical created_at so only the -id tiebreaker can order them.
        Post.objects.filter(pk__in=[p.pk for p in posts]).update(created_at=stamp)
        return list(Post.objects.filter(owner=user).order_by("-created_at", "-id"))

    def test_atk_r004_identical_created_at_windows_stable_and_duplicate_free(self, api_client):
        user = make_user()
        expected = self._same_timestamp_posts(user, 5)
        expected_ids = [str(p.pk) for p in expected]
        auth_client(api_client, user)

        seen: list[str] = []
        for offset in range(0, 5, 2):
            resp = api_client.get(POSTS_URL, {"limit": 2, "offset": offset})
            assert resp.status_code == 200
            seen.extend(item["id"] for item in resp.json())
        assert seen == expected_ids, "pagination windows unstable/duplicated on tied created_at"

    def test_atk_r005_feed_uses_same_order_pair_as_listing(self):
        user = make_user()
        followed = make_user(username="bob", email="bob@example.com")
        from apps.social.models import Follow

        Follow.objects.create(follower=user, following=followed)
        expected = self._same_timestamp_posts(followed, 4)
        feed = FeedService().list_feed(user)
        assert [p.pk for p in feed] == [p.pk for p in expected]

    def test_atk_r006_caption_update_does_not_change_ordering(self, api_client):
        user = make_user()
        posts = self._same_timestamp_posts(user, 3)
        auth_client(api_client, user)
        resp = api_client.patch(f"{POSTS_URL}{posts[2].pk}/", {"caption": "edited"})
        assert resp.status_code == 200
        resp = api_client.get(POSTS_URL, {"limit": 10})
        assert [item["id"] for item in resp.json()] == [str(p.pk) for p in posts]
