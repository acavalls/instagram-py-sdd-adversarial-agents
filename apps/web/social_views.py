"""Web views for the social capability (thin, design decision 6).

The follow/unfollow HTMX views only shape the request, call the use cases
and render the ``_follow_button.html`` partial with the new button state
plus the inline toast (same pattern as the posts web layer's card
responses): every business rule (self-follow, duplicate pair, unknown
relationship) lives in the use cases, services and models, and the error
strings the toast shows flow from the use-case output unchanged. The
profile page view composes the posts listing use case for the grid, the
follow service for the relationship flag and plain state lookups for the
counters (design decision 8).
"""

import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.use_cases import ListPostsInput, ListPostsUseCase
from apps.social.services import FollowService
from apps.social.use_cases import (
    FollowUserInput,
    FollowUserUseCase,
    UnfollowUserInput,
    UnfollowUserUseCase,
)
from apps.web.post_views import current_user
from apps.web.views import FEED_PAGE_SIZE

# Toast texts (design decision 6): confirmed by the HTMX swap that also
# toggles the button in place (social spec: Follow and unfollow actions).
FOLLOW_SUCCESS_TOAST = "Followed successfully"

UNFOLLOW_SUCCESS_TOAST = "Unfollowed successfully"

# Page size of the profile post grid: the same window as the home feed
# (design decision 8 reuses the home pagination for consistency).
PROFILE_PAGE_SIZE = FEED_PAGE_SIZE


def _button_response(
    request: HttpRequest,
    *,
    target_user: User,
    is_following: bool,
    toast_message: str,
    toast_tags: str,
) -> HttpResponse:
    """Render the follow button partial with the given state and toast.

    The HTMX swap replaces the whole wrapper (button + toast), so the
    response both toggles the button in place and confirms with a toast
    (social spec: Web follow via HTMX / Web unfollow via HTMX). On failure
    the caller passes the current relationship state back, so the button
    keeps it while the toast shows the failure reason (social spec: Web
    follow failure shows the cause).
    """
    return render(
        request,
        "web/_follow_button.html",
        {
            "target_user": target_user,
            "is_following": is_following,
            "toast_message": toast_message,
            "toast_tags": toast_tags,
        },
    )


@login_required
@require_POST
def follow_user(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Follow the target user and return the following-state button plus the
    "Followed successfully" toast (social spec: Web follow via HTMX).

    Use case errors (self-follow, duplicate pair) answer as an error toast
    with the exact reference error text and the button keeping its current
    state (social spec: Web follow failure shows the cause). An unknown
    target identifier is an edge format rule: 404, like the profile page
    (design decision 8).
    """
    target_user = get_object_or_404(User, pk=user_id)
    viewer = current_user(request)
    output = FollowUserUseCase().execute(FollowUserInput(user=viewer, target_user=target_user))
    if output.success:
        return _button_response(
            request,
            target_user=target_user,
            is_following=True,
            toast_message=FOLLOW_SUCCESS_TOAST,
            toast_tags="success",
        )
    assert output.error is not None  # a failed follow always reports an error
    return _button_response(
        request,
        target_user=target_user,
        # The current state, so the button keeps it on failure.
        is_following=FollowService().is_following(viewer, target_user),
        toast_message=output.error,
        toast_tags="error",
    )


@login_required
@require_POST
def unfollow_user(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Unfollow the target user and return the follow-state button plus the
    "Unfollowed successfully" toast (social spec: Web unfollow via HTMX).

    Use case errors (unknown relationship) answer as an error toast with the
    exact reference error text and the button keeping its current state
    (social spec: Web follow failure shows the cause). An unknown target
    identifier answers 404, like the follow view.
    """
    target_user = get_object_or_404(User, pk=user_id)
    viewer = current_user(request)
    output = UnfollowUserUseCase().execute(UnfollowUserInput(user=viewer, target_user=target_user))
    if output.success:
        return _button_response(
            request,
            target_user=target_user,
            is_following=False,
            toast_message=UNFOLLOW_SUCCESS_TOAST,
            toast_tags="success",
        )
    assert output.error is not None  # a failed unfollow always reports an error
    return _button_response(
        request,
        target_user=target_user,
        # The current state, so the button keeps it on failure.
        is_following=FollowService().is_following(viewer, target_user),
        toast_message=output.error,
        toast_tags="error",
    )


def _parse_page(request: HttpRequest) -> int:
    """Parse the ``page`` query parameter, clamping it to the first page.

    Same edge rule as the home feed (design decision 4): a missing or
    non-numeric parameter falls back to page 1.
    """
    try:
        page = int(request.GET.get("page", "1"))
    except ValueError:
        page = 1
    return max(page, 1)


@login_required
def profile_view(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Profile page of any user (social spec: User profile page, design
    decision 8): their posts newest first through ``PostService.list_for_user``
    (via ``ListPostsUseCase``, 12 per page with the home prev/next window),
    the posts/followers/following counters as plain state lookups, and the
    ``is_own_profile`` / ``is_following`` flags the template branches on
    (edit/delete controls on the owner's grid, follow button for visitors).
    An unknown identifier answers 404 (social spec: Unknown profile
    responds 404); the page requires login like every protected page
    (design decision 7)."""
    profile_user = get_object_or_404(User, pk=user_id)
    viewer = current_user(request)
    page = _parse_page(request)
    offset = (page - 1) * PROFILE_PAGE_SIZE
    posts = (
        ListPostsUseCase()
        .execute(ListPostsInput(user=profile_user, limit=PROFILE_PAGE_SIZE, offset=offset))
        .posts
    )
    context = {
        "profile_user": profile_user,
        "posts": posts,
        # Counters are state lookups, not business rules (task 6.1).
        "posts_count": Post.objects.filter(owner=profile_user).count(),
        "followers_count": profile_user.followers.count(),
        "following_count": profile_user.following.count(),
        "is_own_profile": viewer.pk == profile_user.pk,
        "is_following": FollowService().is_following(viewer, profile_user),
        "page": page,
        "prev_page": page - 1 if page > 1 else None,
        # A full window implies there may be more posts on the next page.
        "next_page": page + 1 if len(posts) == PROFILE_PAGE_SIZE else None,
    }
    return render(request, "web/profile.html", context)


@login_required
def following_list(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Following-list modal of any profile (social spec: Following list,
    design decision 9): the users that profile follows, newest relationship
    first, optionally filtered by the ``q`` query — the search is a query
    concern that lives in ``FollowService.get_following`` (icontains on
    username/first_name/last_name), the view only composes it. An unknown
    identifier answers 404, like the profile page; the modal requires login
    like every protected page (design decision 7)."""
    profile_user = get_object_or_404(User, pk=user_id)
    query = request.GET.get("q", "").strip()
    following_users = FollowService().get_following(profile_user, q=query or None)
    return render(
        request,
        "web/_following_list_modal.html",
        {"profile_user": profile_user, "following_users": following_users, "q": query},
    )
