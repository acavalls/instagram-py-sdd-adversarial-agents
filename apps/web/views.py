import json
import uuid

from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User, validate_username
from apps.accounts.services import UserService
from apps.accounts.use_cases import (
    ERROR_INVALID_CREDENTIALS,
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)
from apps.posts.models import PostMedia
from apps.posts.services import PostMediaInput, PostService
from apps.posts.services.media_generator import generate_placeholder_image, random_caption
from apps.posts.use_cases import (
    ERROR_POST_EDIT_FORBIDDEN,
    ERROR_POST_NOT_FOUND,
    CreatePostInput,
    CreatePostUseCase,
    DeletePostInput,
    DeletePostUseCase,
    GetPostInput,
    GetPostUseCase,
    UpdatePostInput,
    UpdatePostUseCase,
)
from apps.social.services import FeedService, FollowService
from apps.social.use_cases import (
    FollowUserInput,
    FollowUserOutput,
    FollowUserUseCase,
    GetUserSuggestionsInput,
    GetUserSuggestionsUseCase,
    ListFeedInput,
    ListFeedUseCase,
    UnfollowUserInput,
    UnfollowUserOutput,
    UnfollowUserUseCase,
)

REGISTER_SUCCESS_MESSAGE = "Account created successfully. Please login."
LOGIN_SUCCESS_MESSAGE = "Logged in successfully"
LOGOUT_SUCCESS_MESSAGE = "You have been logged out"
LOGIN_PAGE = "/web/login/"
FEED_PAGE = "/web/feed/"
ERROR_PASSWORD_TOO_SHORT = "Password must be at least 8 characters"
PASSWORD_MIN_LENGTH = 8
POST_CREATE_SUCCESS_MESSAGE = "Post created!"
POST_UPDATE_SUCCESS_MESSAGE = "Post updated!"
POST_DELETE_SUCCESS_MESSAGE = "Post deleted!"
FOLLOW_SUCCESS_MESSAGE = "Followed successfully"
UNFOLLOW_SUCCESS_MESSAGE = "Unfollowed successfully"
FOLLOW_BUTTON_PARTIAL = "web/partials/follow_button.html"
FOLLOWING_LIST_PAGE = "web/following_list.html"
FOLLOWING_LIST_PARTIAL = "web/partials/_following_list_modal.html"
FEED_PAGE_SIZE = 12
PROFILE_PAGE_SIZE = 12
HX_REQUEST_HEADER = "HX-Request"


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _register(request)
    return render(request, "web/register.html")


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return _login(request)
    if request.user.is_authenticated:
        return redirect(FEED_PAGE)
    return render(request, "web/login.html")


def _login(request: HttpRequest) -> HttpResponse:
    username = request.POST.get("username", "")
    password = request.POST.get("password", "")

    use_case = AuthenticateUserUseCase()
    output = use_case.execute(AuthenticateUserInput(username=username, password=password))
    if not output.success or output.user is None:
        return _render_login_with_error(request, ERROR_INVALID_CREDENTIALS, username=username)

    django_login(request, output.user)
    messages.success(request, LOGIN_SUCCESS_MESSAGE)
    return redirect(FEED_PAGE)


def _render_login_with_error(request: HttpRequest, error: str, *, username: str) -> HttpResponse:
    return render(request, "web/login.html", {"error": error, "username": username})


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    django_logout(request)
    messages.success(request, LOGOUT_SUCCESS_MESSAGE)
    return redirect(LOGIN_PAGE)


@login_required
def feed_view(request: HttpRequest) -> HttpResponse:
    """The home feed: the followed users' posts as cards, newest first.

    HTMX requests (the scroll sentinel) receive only the window of cards
    plus the next sentinel or the end marker, without the page shell; a
    non-HTMX request with a page parameter renders the full page with that
    window. When the user follows nobody the primary empty state invites
    them to share their first photo; when they follow people but none of
    them has posts, a secondary empty state replaces the cards.
    """
    page = _feed_page(request)
    output = ListFeedUseCase(feed_service=FeedService()).execute(
        ListFeedInput(
            user=_request_user(request),
            limit=FEED_PAGE_SIZE + 1,
            offset=(page - 1) * FEED_PAGE_SIZE,
        )
    )
    posts = output.posts[:FEED_PAGE_SIZE]
    has_next = len(output.posts) > FEED_PAGE_SIZE
    context = {
        "posts": posts,
        "page": page,
        "has_next": has_next,
        "follows_anyone": output.follows_anyone,
    }
    if _is_htmx(request):
        return render(request, "web/partials/post_cards.html", context)
    context["suggestions"] = _feed_suggestions(request)
    return render(request, "web/feed.html", context)


def _feed_suggestions(request: HttpRequest) -> list[User]:
    """Up to 5 accounts the requester does not follow, newest accounts first.

    Rendered by the home feed sidebar (the suggestions column beside the
    feed grid); HTMX card windows never render the sidebar so they skip
    this query.
    """
    output = GetUserSuggestionsUseCase(feed_service=FeedService()).execute(
        GetUserSuggestionsInput(user=_request_user(request))
    )
    return output.suggestions


@login_required
def profile_view(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """A user's profile page: header stats plus the posts grid, newest first.

    HTMX requests (the scroll sentinel) receive only the next window of grid
    items plus the next sentinel or the end marker, without the page shell;
    a non-HTMX request with a page parameter renders the full page with that
    window. On other profiles the follow button reflects the current
    relationship (the toggle endpoints belong to the follow group).
    """
    profile_user = User.objects.filter(pk=user_id).first()
    if profile_user is None:
        raise Http404("User not found")
    page = _feed_page(request)
    window = PostService().list_for_user(
        profile_user,
        limit=PROFILE_PAGE_SIZE + 1,
        offset=(page - 1) * PROFILE_PAGE_SIZE,
    )
    posts = window[:PROFILE_PAGE_SIZE]
    has_next = len(window) > PROFILE_PAGE_SIZE
    follow_service = FollowService()
    is_own_profile = profile_user == _request_user(request)
    context = {
        "profile_user": profile_user,
        "posts": posts,
        "page": page,
        "has_next": has_next,
        "posts_count": len(PostService().list_for_user(profile_user)),
        "followers_count": len(follow_service.get_followers(profile_user)),
        "following_count": len(follow_service.get_following(profile_user)),
        "is_own_profile": is_own_profile,
        "is_following": (
            False
            if is_own_profile
            else follow_service.is_following(_request_user(request), profile_user)
        ),
    }
    if _is_htmx(request):
        return render(request, "web/partials/profile_grid.html", context)
    return render(request, "web/profile.html", context)


@require_http_methods(["GET"])
@login_required
def following_list_view(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """The following-list modal of a profile: GET /web/profile/<user_id>/following/.

    Part of the profile-scoped route family (profile page, follow toggle
    endpoints): the profile's following stat link points here. A plain
    request renders the modal as a page; the search box re-requests the
    same endpoint through HTMX GET and the response (the modal partial
    with the `q`-filtered list) swaps the modal in place. `q` filters the
    followed users by username or name, case-insensitively (icontains).
    """
    profile_user = User.objects.filter(pk=user_id).first()
    if profile_user is None:
        raise Http404("User not found")
    query = request.GET.get("q", "")
    context = {
        "profile_user": profile_user,
        "users": _search_following(FollowService().get_following(profile_user), query),
        "q": query,
    }
    if _is_htmx(request):
        return render(request, FOLLOWING_LIST_PARTIAL, context)
    return render(request, FOLLOWING_LIST_PAGE, context)


def _search_following(users: list[User], query: str) -> list[User]:
    """Followed users whose username or name matches the query (icontains).

    Case-insensitive substring match over the list returned by
    `FollowService.get_following` (newest relationship first), mirroring
    the ORM's icontains semantics on username, first_name and last_name.
    """
    if not query:
        return users
    needle = query.lower()
    return [
        user
        for user in users
        if needle in user.username.lower()
        or needle in user.first_name.lower()
        or needle in user.last_name.lower()
    ]


@require_http_methods(["POST"])
@login_required
def follow_user_view(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """HTMX follow action: POST /web/profile/<user_id>/follow/.

    Part of the profile-scoped route family (profile page, following
    modal). Answers with the follow button partial in the new (following)
    state plus the "Followed successfully" toast; a failure answers with
    the button in its current (unchanged) state and an error toast
    carrying the failure reason.
    """
    return _toggle_follow(request, user_id, following_requested=True)


@require_http_methods(["POST"])
@login_required
def unfollow_user_view(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """HTMX unfollow action: POST /web/profile/<user_id>/unfollow/.

    Same contract as the follow action, mirrored: success answers the
    button back in the follow state with the "Unfollowed successfully"
    toast; a failure keeps the following state and reports the reason.
    """
    return _toggle_follow(request, user_id, following_requested=False)


def _toggle_follow(
    request: HttpRequest, user_id: uuid.UUID, *, following_requested: bool
) -> HttpResponse:
    """Run the follow/unfollow use case and answer the button fragment.

    Success re-renders the button in the new state; failure re-renders it
    in its current (unchanged) state — the actual relationship is never
    altered by a failed action — with the use case's error as the toast
    reason (self-follow, duplicate, or unknown relationship).
    """
    target_user = User.objects.filter(pk=user_id).first()
    if target_user is None:
        raise Http404("User not found")
    follower = _request_user(request)
    output: FollowUserOutput | UnfollowUserOutput
    if following_requested:
        output = FollowUserUseCase(follow_service=FollowService()).execute(
            FollowUserInput(follower=follower, following=target_user)
        )
    else:
        output = UnfollowUserUseCase(follow_service=FollowService()).execute(
            UnfollowUserInput(follower=follower, following=target_user)
        )
    if output.success:
        return _follow_button_response(
            request,
            target_user,
            is_following=following_requested,
            toast=FOLLOW_SUCCESS_MESSAGE if following_requested else UNFOLLOW_SUCCESS_MESSAGE,
        )
    current_state = FollowService().is_following(follower, target_user)
    return _follow_button_response(
        request,
        target_user,
        is_following=current_state,
        toast=output.error or "The action could not be completed",
    )


def _follow_button_response(
    request: HttpRequest, target_user: User, *, is_following: bool, toast: str
) -> HttpResponse:
    response = render(
        request,
        FOLLOW_BUTTON_PARTIAL,
        {"target_user": target_user, "is_following": is_following},
    )
    response["HX-Trigger"] = json.dumps({"toast": toast})
    return response


@require_http_methods(["POST"])
@login_required
def create_post_view(request: HttpRequest) -> HttpResponse:
    """Create a post from the sidebar form: random caption + placeholder image."""
    use_case = CreatePostUseCase(post_service=PostService())
    output = use_case.execute(
        CreatePostInput(
            user=_request_user(request),
            caption=random_caption(),
            media=(
                PostMediaInput(
                    file=generate_placeholder_image(seed=str(uuid.uuid4())),
                    media_type=PostMedia.MediaType.IMAGE,
                ),
            ),
        )
    )
    if not output.success:
        messages.error(request, output.error or "The post could not be created")
        return redirect(FEED_PAGE)
    messages.success(request, POST_CREATE_SUCCESS_MESSAGE)
    return redirect(FEED_PAGE)


@login_required
def post_card_view(request: HttpRequest, post_id: uuid.UUID) -> HttpResponse:
    """A single post card fragment (used to close the inline edit form)."""
    output = GetPostUseCase(post_service=PostService()).execute(
        GetPostInput(user=_request_user(request), post_id=post_id)
    )
    if not output.success or output.post is None:
        raise Http404("Post not found")
    return render(request, "web/partials/post_card.html", {"post": output.post})


@require_http_methods(["GET", "POST"])
@login_required
def post_edit_view(request: HttpRequest, post_id: uuid.UUID) -> HttpResponse:
    """Inline caption edit on the card.

    GET returns the edit form fragment; POST (the form submit) updates the
    caption and answers with the updated card fragment plus the "Post
    updated!" toast.     An unknown or non-owner post id closes the form without changing
    anything (empty response, the form swap removes it); a GET for an
    unknown or non-owner post id answers 404 like the card fragment.
    """
    if request.method == "GET":
        return _render_edit_form(request, post_id)

    output = UpdatePostUseCase(post_service=PostService()).execute(
        UpdatePostInput(
            user=_request_user(request), post_id=post_id, caption=_post_caption(request)
        )
    )
    if output.success and output.post is not None:
        response = render(request, "web/partials/post_card.html", {"post": output.post})
        response["HX-Trigger"] = json.dumps({"toast": POST_UPDATE_SUCCESS_MESSAGE})
        return response
    if output.error == ERROR_POST_NOT_FOUND:
        return HttpResponse()
    if output.error == ERROR_POST_EDIT_FORBIDDEN:
        return HttpResponse(output.error, status=403)
    return _render_edit_form(request, post_id, error=output.error)


def _render_edit_form(
    request: HttpRequest, post_id: uuid.UUID, *, error: str | None = None
) -> HttpResponse:
    """Render the inline edit form, or 404 for unknown/non-owner posts.

    The fetch goes through the ownership-aware use case: a non-owner's
    post is treated as non-existent (404), never leaked into the form.
    """
    output = GetPostUseCase(post_service=PostService()).execute(
        GetPostInput(user=_request_user(request), post_id=post_id)
    )
    if not output.success or output.post is None:
        raise Http404("Post not found")
    return render(
        request,
        "web/partials/post_edit_form.html",
        {"post": output.post, "error": error},
    )


@require_http_methods(["POST"])
@login_required
def post_delete_view(request: HttpRequest, post_id: uuid.UUID) -> HttpResponse:
    """Delete the post from its card.

    HTMX requests get an empty response (the card swap removes it) plus
    the "Post deleted!" toast; a plain form post redirects to the feed
    with the same toast. A non-owner is refused with 403.
    """
    output = DeletePostUseCase(post_service=PostService()).execute(
        DeletePostInput(user=_request_user(request), post_id=post_id)
    )
    if output.success:
        if _is_htmx(request):
            response = HttpResponse()
            response["HX-Trigger"] = json.dumps({"toast": POST_DELETE_SUCCESS_MESSAGE})
            return response
        messages.success(request, POST_DELETE_SUCCESS_MESSAGE)
        return redirect(FEED_PAGE)
    if output.error == ERROR_POST_NOT_FOUND:
        return HttpResponse(output.error, status=404)
    return HttpResponse(output.error, status=403)


def _request_user(request: HttpRequest) -> User:
    """The authenticated user (guaranteed by @login_required on the callers)."""
    user = request.user
    assert isinstance(user, User)
    return user


def _feed_page(request: HttpRequest) -> int:
    """The requested feed window page (1-based); anything invalid is page 1."""
    try:
        return max(int(request.GET.get("page", "1")), 1)
    except ValueError:
        return 1


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get(HX_REQUEST_HEADER) == "true"


def _post_caption(request: HttpRequest) -> str:
    return request.POST.get("caption", "")


def _register(request: HttpRequest) -> HttpResponse:
    username = request.POST.get("username", "")
    email = request.POST.get("email", "")
    password = request.POST.get("password", "")

    errors = _validate_fields(username=username, email=email, password=password)
    if errors:
        return _render_with_errors(request, errors, username=username, email=email)

    use_case = RegisterUserUseCase(user_service=UserService())
    output = use_case.execute(RegisterUserInput(username=username, email=email, password=password))
    if not output.success:
        return _render_with_errors(
            request, [output.error or "Invalid data"], username=username, email=email
        )

    messages.success(request, REGISTER_SUCCESS_MESSAGE)
    return redirect("/web/login/")


def _validate_fields(*, username: str, email: str, password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(ERROR_PASSWORD_TOO_SHORT)
    errors.extend(_field_errors(validate_username, username))
    errors.extend(_field_errors(validate_email, email))
    return errors


def _field_errors(validator, value: str) -> list[str]:
    try:
        validator(value)
    except ValidationError as exc:
        return [message for message in exc.messages if isinstance(message, str)]
    return []


def _render_with_errors(
    request: HttpRequest, errors: list[str], *, username: str, email: str
) -> HttpResponse:
    return render(
        request,
        "web/register.html",
        {"errors": errors, "username": username, "email": email},
    )
