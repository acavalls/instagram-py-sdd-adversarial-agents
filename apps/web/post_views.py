"""Web (HTMX) views for the posts capability (thin, design decision 6).

The views only shape the request, call the use cases and render the HTMX
partials (post card, edit form, toast): every business rule (ownership,
caption limit, persistence) lives in the use cases, services and models.
Placeholder post generation also lives here (design decision 4): the web
layer builds the random caption + generated 1x1 GIF, and the use case
receives the file like any other uploaded media.
"""

import random
import uuid
from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.posts.models import CAPTION_MAX_LENGTH, CAPTION_TOO_LONG_ERROR
from apps.posts.use_cases import (
    CreatePostInput,
    CreatePostUseCase,
    DeletePostInput,
    DeletePostUseCase,
    GetPostInput,
    GetPostUseCase,
    UpdatePostInput,
    UpdatePostUseCase,
)

# Feed page URL: defined here (posts web layer) and re-used by the login
# redirect in apps/web/views.py, so no web module imports the other.
FEED_PAGE_URL = "/web/feed/"

CREATE_SUCCESS_TOAST = "Post created!"
UPDATE_SUCCESS_TOAST = "Post updated!"
DELETE_SUCCESS_TOAST = "Post deleted!"

# Fixed in-code caption list for placeholder posts (design decision 4).
PLACEHOLDER_CAPTIONS = [
    "Golden hour vibes ✨",
    "Sunday walk in the city",
    "Coffee first, everything else later",
    "New post, who dis?",
    "Late night coding session",
    "Beach day with friends",
    "Homemade pasta night 🍝",
    "Exploring the old town",
    "Sunset from the rooftop",
    "Weekend reset complete",
]

# Minimal valid 1x1 transparent GIF (same bytes the API tests use), used as
# the generated placeholder media file.
PLACEHOLDER_GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def current_user(request: HttpRequest) -> User:
    """Return the authenticated user (every caller is ``@login_required``)."""
    return cast(User, request.user)


def _build_placeholder_media() -> SimpleUploadedFile:
    """Build the generated placeholder image (design decision 4).

    A 1x1 GIF with a random color in the filename so consecutive placeholder
    posts do not collide in the media storage.
    """
    color = f"{random.randint(0, 0xFFFFFF):06x}"
    return SimpleUploadedFile(
        f"placeholder-{color}.gif", PLACEHOLDER_GIF_BYTES, content_type="image/gif"
    )


def _card_response(
    request: HttpRequest,
    post: object,
    *,
    toast_message: str | None = None,
    toast_tags: str = "success",
) -> HttpResponse:
    """Render the post card partial (optionally with an inline toast)."""
    return render(
        request,
        "web/post_card.html",
        {"post": post, "toast_message": toast_message, "toast_tags": toast_tags},
    )


def _toast_response(request: HttpRequest, *, toast_message: str, toast_tags: str) -> HttpResponse:
    """Render a toast-only partial: the HTMX swap replaces the card with the
    toast, which both closes the form / removes the card and surfaces the
    message."""
    return render(
        request, "web/post_toast.html", {"toast_message": toast_message, "toast_tags": toast_tags}
    )


@login_required
@require_POST
def create_post(request: HttpRequest) -> HttpResponse:
    """Create a placeholder post from the feed page and redirect back with a
    toast (spec: Successful web creation)."""
    output = CreatePostUseCase().execute(
        CreatePostInput(
            owner=current_user(request),
            caption=random.choice(PLACEHOLDER_CAPTIONS),
            media_files=[_build_placeholder_media()],
        )
    )
    if output.success:
        messages.success(request, CREATE_SUCCESS_TOAST)
    else:
        assert output.error is not None  # a failed creation always has an error
        messages.error(request, output.error)
    return redirect(FEED_PAGE_URL)


@login_required
def edit_form(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Return the inline edit form partial (spec: Inline web edit).

    An unknown identifier or another user's post (posts are visible only
    through their owner's content listings, delta spec: Post visibility)
    closes the form without rendering anything instead of crashing (spec:
    Cancel inline edit — unknown post id case).
    """
    output = GetPostUseCase().execute(GetPostInput(post_id=pk, user=current_user(request)))
    if not output.success or output.post is None:
        return HttpResponse("")
    return render(request, "web/post_edit_form.html", {"post": output.post})


@login_required
def cancel_edit(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Return the original card partial, closing the edit form without any
    change (spec: Cancel inline edit). A non-owner (or unknown id) gets an
    empty response — never the other user's post."""
    output = GetPostUseCase().execute(GetPostInput(post_id=pk, user=current_user(request)))
    if not output.success or output.post is None:
        return HttpResponse("")
    return _card_response(request, output.post)


@login_required
@require_POST
def submit_edit(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Update the caption and return the refreshed card plus the "Post
    updated!" toast (spec: Inline web edit).

    Use case errors (ownership or unknown id) answer as error toasts with the
    exact model error text, closing the form without changing the post. The
    caption length is a field-format rule checked in the web layer (mirroring
    the register view) so a crafted POST never reaches a 500.
    """
    caption = request.POST.get("caption", "")
    if len(caption) > CAPTION_MAX_LENGTH:
        return _toast_response(request, toast_message=CAPTION_TOO_LONG_ERROR, toast_tags="error")
    output = UpdatePostUseCase().execute(
        UpdatePostInput(post_id=pk, user=current_user(request), caption=caption)
    )
    if output.success:
        assert output.post is not None  # a successful update always yields a post
        return _card_response(
            request, output.post, toast_message=UPDATE_SUCCESS_TOAST, toast_tags="success"
        )
    assert output.error is not None  # a failed update always reports an error
    return _toast_response(request, toast_message=output.error, toast_tags="error")


@login_required
@require_POST
def delete_post(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Delete the post and replace the card with the "Post deleted!" toast
    (spec: Web deletion removes the card).

    Use case errors (non-owner or unknown id) answer as error toasts with the
    exact model error text.
    """
    output = DeletePostUseCase().execute(DeletePostInput(post_id=pk, user=current_user(request)))
    if output.success:
        return _toast_response(request, toast_message=DELETE_SUCCESS_TOAST, toast_tags="success")
    assert output.error is not None  # a failed deletion always reports an error
    return _toast_response(request, toast_message=output.error, toast_tags="error")
