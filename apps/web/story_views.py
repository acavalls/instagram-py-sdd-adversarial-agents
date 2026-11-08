"""Web stories surface: creation, viewing and the stories bar fragment.

The endpoints follow the HTMX out-of-band idiom the feed and follow
buttons already use: the response body carries the out-of-band re-render
of the stories bar (and the consumed toast messages), so an HTMX client
updates the bar in place without a page reload; a plain (non-HTMX) POST
falls back to a redirect to the feed with the same toast.
"""

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.posts.services import StoryFeedGroup, StoryService
from apps.posts.use_cases import (
    CreateStoryInput,
    CreateStoryUseCase,
    ListFeedStoriesInput,
    ListFeedStoriesUseCase,
    ViewStoryInput,
    ViewStoryUseCase,
)
from apps.social.services import FollowService

STORY_CREATE_SUCCESS_MESSAGE = "Story created"
STORY_VIEW_SUCCESS_MESSAGE = "Story viewed"
STORY_CREATE_ERROR_MESSAGE = "The story could not be created"
STORY_VIEW_ERROR_MESSAGE = "The story could not be viewed"
FEED_PAGE = "/web/feed/"
TOAST_WITH_STORIES_PARTIAL = "web/partials/_toast_with_stories.html"
HX_REQUEST_HEADER = "HX-Request"


def stories_bar_context(user: User) -> dict[str, list[StoryFeedGroup]]:
    """Build the stories-bar template context for `user`.

    The shared builder behind every bar render: the out-of-band responses
    of the story endpoints and (through the feed view) the home page use
    the same listing, so the bar always shows the followed users' active
    story groups in bar order (unviewed groups first).
    """
    output = ListFeedStoriesUseCase(story_service=StoryService()).execute(
        ListFeedStoriesInput(user=user)
    )
    return {"story_groups": output.groups}


@require_http_methods(["POST"])
@login_required
def create_story_view(request: HttpRequest) -> HttpResponse:
    """Create a story: POST /web/stories/create/.

    The media is generated automatically (no upload); on success the
    response carries the "Story created" toast and an out-of-band
    re-render of the stories bar.
    """
    output = CreateStoryUseCase(story_service=StoryService()).execute(
        CreateStoryInput(user=_request_user(request))
    )
    if not output.success:
        return _stories_toast_response(
            request, output.error or STORY_CREATE_ERROR_MESSAGE, level="error"
        )
    return _stories_toast_response(request, STORY_CREATE_SUCCESS_MESSAGE, level="success")


@require_http_methods(["POST"])
@login_required
def view_story_view(request: HttpRequest, story_id: uuid.UUID) -> HttpResponse:
    """Record a view of a followed user's active story.

    POST /web/stories/<story_id>/view/: on success the response carries
    the "Story viewed" toast and an out-of-band re-render of the stories
    bar (so the group's ring state and order update). Every rejection
    answers HTTP 200 with the use case's exact error toast and the same
    out-of-band bar re-render, without recording any view.
    """
    output = ViewStoryUseCase(story_service=StoryService(), follow_service=FollowService()).execute(
        ViewStoryInput(story_id=story_id, viewer=_request_user(request))
    )
    if output.success:
        return _stories_toast_response(request, STORY_VIEW_SUCCESS_MESSAGE, level="success")
    return _stories_toast_response(request, output.error or STORY_VIEW_ERROR_MESSAGE, level="error")


def _stories_toast_response(request: HttpRequest, toast: str, *, level: str) -> HttpResponse:
    """Answer a story action with the toast plus the out-of-band stories bar.

    HTMX requests receive the toast-with-stories partial: it swaps the
    page's messages container out of band with the new toast and replaces
    the stories bar out of band with a fresh render. Plain form posts
    redirect to the feed, where the message framework shows the toast.
    """
    if level == "success":
        messages.success(request, toast)
    else:
        messages.error(request, toast)
    if _is_htmx(request):
        return render(
            request,
            TOAST_WITH_STORIES_PARTIAL,
            stories_bar_context(_request_user(request)),
        )
    return redirect(FEED_PAGE)


def _request_user(request: HttpRequest) -> User:
    """The authenticated user (guaranteed by @login_required on the callers)."""
    user = request.user
    assert isinstance(user, User)
    return user


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get(HX_REQUEST_HEADER) == "true"
