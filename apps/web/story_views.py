"""Web (HTMX) views for the stories capability (thin, design decision 5).

The views only shape the request, call the use cases and render the
``_toast_with_stories.html`` partial (toast + out-of-band stories bar
re-render): every business rule (placeholder media generation, view rules,
expiry) lives in the use cases, services and models. The toast flows through
the messages framework — the same HTMX conventions as the follow button
partial (design decision 5), with the stories bar swapped out-of-band by id.
"""

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.posts.use_cases import (
    CreateStoryInput,
    CreateStoryUseCase,
    ListFeedStoriesInput,
    ListFeedStoriesUseCase,
    ViewStoryInput,
    ViewStoryUseCase,
)
from apps.web.post_views import current_user

# Toast texts (stories spec: Story creation, Story view tracking).
CREATE_STORY_SUCCESS_TOAST = "Story created"

VIEW_STORY_SUCCESS_TOAST = "Story viewed"


def _stories_response(request: HttpRequest, *, toast_message: str, toast_tags: str) -> HttpResponse:
    """Render the toast + out-of-band stories bar partial (design decision 5).

    The toast goes through the messages framework into the ``#stories-toasts``
    container (rendered outside the bar by the feed template, so the OOB bar
    swap never erases it); the stories bar is re-rendered from the viewer's
    current feed stories and swapped out-of-band by id. On failure the error
    text flows from the use-case output unchanged, like every other web toast.
    """
    if toast_tags == "success":
        messages.success(request, toast_message)
    else:
        messages.error(request, toast_message)
    story_groups = (
        ListFeedStoriesUseCase()
        .execute(ListFeedStoriesInput(viewer=current_user(request)))
        .story_groups
    )
    return render(request, "web/_toast_with_stories.html", {"story_groups": story_groups})


@login_required
@require_POST
def create_story(request: HttpRequest) -> HttpResponse:
    """Create a placeholder story for the logged-in user and answer with the
    "Story created" toast plus the out-of-band re-rendered stories bar
    (stories spec: Successful web creation).

    POST-only and login-required like every state-changing web endpoint (the
    same convention as the web logout and the follow buttons).
    """
    output = CreateStoryUseCase().execute(CreateStoryInput(owner=current_user(request)))
    if output.success:
        return _stories_response(
            request, toast_message=CREATE_STORY_SUCCESS_TOAST, toast_tags="success"
        )
    assert output.error is not None  # a failed creation always reports an error
    return _stories_response(request, toast_message=output.error, toast_tags="error")


@login_required
@require_POST
def view_story(request: HttpRequest, story_id: uuid.UUID) -> HttpResponse:
    """Record the viewer's view of a story and answer with the "Story viewed"
    toast plus the out-of-band re-rendered stories bar (stories spec: First
    view recorded).

    Use-case errors (unknown/expired id, self-view, non-followed owner)
    answer as an error toast with the exact use-case error text and the bar
    keeping its current state — the repo convention for HTMX failures (see
    ``apps/web/social_views.py``). A non-UUID identifier never reaches this
    view: the route's ``<uuid:story_id>`` converter answers 404.
    """
    output = ViewStoryUseCase().execute(
        ViewStoryInput(story_id=story_id, viewer=current_user(request))
    )
    if output.success:
        return _stories_response(
            request, toast_message=VIEW_STORY_SUCCESS_TOAST, toast_tags="success"
        )
    assert output.error is not None  # a failed view always reports an error
    return _stories_response(request, toast_message=output.error, toast_tags="error")
