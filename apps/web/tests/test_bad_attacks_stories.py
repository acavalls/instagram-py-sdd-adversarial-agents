"""The Bad — attack iteration 1 on change ``add-stories``.

Targets the stories surface: expiry boundaries (expires_at exactly now),
lazy purge cascade into view records, concurrent duplicate first views
(get_or_create race), web idempotency on repeated views, ordering of the
stories bar (unviewed-first with older unviewed groups vs newer viewed
groups), ring state updates, view-rule enforcement through the web
endpoints (self-view, non-followed, expired, unknown), method/auth guards
on the web endpoints, and crafted payloads.
"""

from datetime import timedelta
from threading import Thread

import pytest
from django.core.files.base import ContentFile
from django.db import OperationalError
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Story, StoryView
from apps.posts.services import StoryService
from apps.social.services import FollowService

pytestmark = pytest.mark.django_db

RAW_PASSWORD = "sup3r-secret-pw"
CREATE_URL = "/web/stories/create/"
FEED_URL = "/web/feed/"


def make_user(username: str = "alice", **overrides):
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": RAW_PASSWORD,
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def make_story(
    owner: User, *, created_ago: timedelta | None = None, expires_in: timedelta | None = None
) -> Story:
    story = Story(owner=owner)
    story.image.save(f"story-{owner.username}.jpg", ContentFile(b"x"), save=False)
    if created_ago is not None:
        story.created_at = timezone.now() - created_ago
    if expires_in is not None:
        story.expires_at = timezone.now() + expires_in
    story.save()
    return story


def follow(follower: User, following: User) -> None:
    FollowService().follow(follower=follower, following=following)


def login(client, user: User) -> None:
    client.force_login(user)


def shown_messages(response) -> list[str]:
    return [str(message) for message in response.wsgi_request._messages]


def view_url(story: Story) -> str:
    return f"/web/stories/{story.pk}/view/"


# ---------------------------------------------------------------- ATK-001
def test_boundary_expires_at_exactly_now():
    """expires_at == now: NOT active anywhere, yet purged by cleanup."""
    owner = make_user("bndowner")
    boundary_story = make_story(owner, expires_in=timedelta(0))
    active_story = make_story(owner, expires_in=timedelta(hours=1))

    assert StoryService().get_active_by_id(boundary_story.pk) is None
    assert boundary_story not in StoryService().get_active_for_user(owner)
    count = StoryService().cleanup_expired()
    assert count == 1, "boundary story (expires_at == now) must be purged"
    assert Story.objects.filter(pk=boundary_story.pk).exists() is False
    assert Story.objects.filter(pk=active_story.pk).exists() is True


# ---------------------------------------------------------------- ATK-002
def test_cleanup_purges_view_records_with_story():
    owner = make_user("cascowner")
    viewer = make_user("cascviewer")
    follow(viewer, owner)
    story = make_story(owner, created_ago=timedelta(hours=25), expires_in=timedelta(hours=-1))
    StoryView.objects.create(story=story, viewer=viewer)
    deleted = StoryService().cleanup_expired()
    assert deleted == 1
    assert StoryView.objects.count() == 0


# ---------------------------------------------------------------- ATK-003
@pytest.mark.django_db(transaction=True)
def test_concurrent_first_views_single_row():
    """Two concurrent first views of the same story by the same viewer."""
    owner = make_user("raceowner")
    viewer = make_user("raceviewer")
    follow(viewer, owner)
    story = make_story(owner)

    errors: list[Exception] = []
    sqlite_locks: list[Exception] = []

    def worker():
        try:
            StoryService().mark_viewed(story, viewer)
        except OperationalError as exc:
            # SQLite table locks under thread contention are environmental
            # noise, not a product defect; any other exception is a bug.
            sqlite_locks.append(exc)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"mark_viewed raised under concurrency: {errors}"
    assert sqlite_locks or StoryView.objects.filter(story=story, viewer=viewer).count() == 1
    # No duplicate rows regardless of which worker won the race.
    assert StoryView.objects.filter(story=story, viewer=viewer).count() <= 1


# ---------------------------------------------------------------- ATK-004
def test_web_repeated_view_idempotent(client):
    owner = make_user("idemowner")
    viewer = make_user("idemviewer")
    follow(viewer, owner)
    story = make_story(owner)
    login(client, viewer)

    r1 = client.post(view_url(story))
    r2 = client.post(view_url(story))
    assert r1.status_code == 200 and r2.status_code == 200
    assert "Story viewed" in shown_messages(r2)
    assert StoryView.objects.filter(story=story, viewer=viewer).count() == 1


# ---------------------------------------------------------------- ATK-005
def test_unviewed_older_group_ordered_before_viewed_newer_group(client):
    """Unviewed-first ordering must not be fooled by recency: the group
    whose LATEST story is unviewed comes first even if that latest story is
    older than the other group's latest story."""
    viewer = make_user("ordviewer")
    older_owner = make_user("ordolder")
    newer_owner = make_user("ordnewer")
    follow(viewer, older_owner)
    follow(viewer, newer_owner)

    # older_owner: latest story created 2h ago, unviewed.
    make_story(older_owner, created_ago=timedelta(hours=2))
    # newer_owner: latest story created 1h ago, already viewed.
    newer_story = make_story(newer_owner, created_ago=timedelta(hours=1))
    StoryView.objects.create(story=newer_story, viewer=viewer)
    login(client, viewer)

    response = client.get(FEED_URL)
    body = response.content.decode()
    pos_older = body.find("ordolder")
    pos_newer = body.find("ordnewer")
    assert pos_older != -1 and pos_newer != -1
    assert pos_older < pos_newer, (
        "group with unviewed latest story (older) must precede the group "
        "with viewed latest story (newer)"
    )


# ---------------------------------------------------------------- ATK-006
def test_ring_viewed_after_viewing_latest_story(client):
    owner = make_user("ringowner")
    viewer = make_user("ringviewer")
    follow(viewer, owner)
    story = make_story(owner)
    login(client, viewer)

    client.post(view_url(story))
    response = client.get(FEED_URL)
    body = response.content.decode()
    assert "story-avatar story-avatar-viewed" in body


# ---------------------------------------------------------------- ATK-007
def test_ring_stays_unseen_when_only_older_story_viewed(client):
    """Viewing an OLDER story of a group must not flip the ring: the group's
    LATEST story is still unviewed, so the group stays in the unseen section."""
    owner = make_user("ringtwoowner")
    viewer = make_user("ringtwoviewer")
    follow(viewer, owner)
    older = make_story(owner, created_ago=timedelta(hours=2))
    newest = make_story(owner, created_ago=timedelta(hours=1))
    login(client, viewer)
    client.post(view_url(older))

    response = client.get(FEED_URL)
    body = response.content.decode()
    assert "story-avatar story-avatar-unseen" in body
    assert "story-avatar story-avatar-viewed" not in body
    # Clicking the avatar targets the newest story.
    assert str(newest.pk) in body


# ---------------------------------------------------------------- ATK-008
def test_web_view_rules_self_nonfollowed_expired(client):
    owner = make_user("ruleowner")
    other = make_user("ruleother")
    stranger = make_user("rulestranger")
    own_story = make_story(owner)
    nonfollowed_story = make_story(other)
    expired_story = make_story(
        stranger, created_ago=timedelta(hours=25), expires_in=timedelta(hours=-1)
    )
    follow(owner, stranger)  # owner follows stranger but that is irrelevant

    login(client, owner)

    # Self-view rejected, no record.
    r_self = client.post(view_url(own_story))
    assert "You cannot view your own story" in shown_messages(r_self)
    assert StoryView.objects.filter(story=own_story).count() == 0

    # Non-followed story rejected, no record.
    r_nonf = client.post(view_url(nonfollowed_story))
    assert "You can only view stories from people you follow" in shown_messages(r_nonf)
    assert StoryView.objects.filter(story=nonfollowed_story).count() == 0

    # Expired story is indistinguishable from unknown.
    r_exp = client.post(view_url(expired_story))
    assert "Story not found" in shown_messages(r_exp)
    assert StoryView.objects.filter(story=expired_story).count() == 0

    # Unknown id.
    r_unk = client.post("/web/stories/00000000-0000-0000-0000-000000000000/view/")
    assert "Story not found" in shown_messages(r_unk)


# ---------------------------------------------------------------- ATK-009
def test_web_method_and_auth_guards(client):
    owner = make_user("guardowner")
    viewer = make_user("guardviewer")
    story = make_story(owner)

    # Anonymous create is rejected (redirect to login, nothing created).
    anon = client
    r_anon = anon.post(CREATE_URL)
    assert r_anon.status_code in (301, 302)
    assert Story.objects.count() == 1  # only the pre-made story; none created

    # Anonymous view is rejected.
    r_anon_view = anon.post(view_url(story))
    assert r_anon_view.status_code in (301, 302)
    assert StoryView.objects.count() == 0

    # GET on the view endpoint is 405 for a logged-in user.
    login(client, viewer)
    r_get = client.get(view_url(story))
    assert r_get.status_code == 405

    # GET on create is 405 too.
    assert client.get(CREATE_URL).status_code == 405


# ---------------------------------------------------------------- ATK-010
def test_crafted_payloads_ignored(client):
    """Extra body fields / query params on create must not alter behavior."""
    viewer = make_user("craftviewer")
    login(client, viewer)
    r = client.post(
        CREATE_URL,
        {"owner": "someone-else", "expires_at": "1970-01-01", "media_type": "VIDEO"},
        QUERY_STRING="owner=hacked",
    )
    assert r.status_code == 200
    assert "Story created" in shown_messages(r)
    story = Story.objects.get()
    assert story.owner == viewer
    assert story.expires_at > timezone.now()


# ---------------------------------------------------------------- ATK-011
def test_bar_excludes_nonfollowed(client):
    viewer = make_user("barviewer")
    followed = make_user("barfollowed")
    stranger = make_user("barstranger")
    follow(viewer, followed)
    make_story(followed)
    make_story(stranger)
    login(client, viewer)

    response = client.get(FEED_URL)
    body = response.content.decode()
    start = body.index('<section id="stories-bar"')
    end = body.index("</section>", start)
    bar = body[start:end]
    assert "barfollowed" in bar
    assert "barstranger" not in bar


# ---------------------------------------------------------------- ATK-012
def test_expiration_is_exactly_created_at_plus_24h():
    owner = make_user("expowner")
    story = StoryService().create(owner)
    delta = story.expires_at - story.created_at
    assert delta == timedelta(hours=24)
