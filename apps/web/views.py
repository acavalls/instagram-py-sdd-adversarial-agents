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
    ListPostsInput,
    ListPostsUseCase,
    UpdatePostInput,
    UpdatePostUseCase,
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
FEED_PAGE_SIZE = 10
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
    """Personal feed: the logged-in user's own posts as cards, newest first.

    HTMX requests (the scroll sentinel) receive only the window of cards
    plus the next sentinel or the end marker, without the page shell; a
    non-HTMX request with a page parameter renders the full page with that
    window. The interim content source is the user's own posts (package 03
    replaces it with the followed-users feed).
    """
    page = _feed_page(request)
    output = ListPostsUseCase(post_service=PostService()).execute(
        ListPostsInput(
            user=_request_user(request),
            limit=FEED_PAGE_SIZE + 1,
            offset=(page - 1) * FEED_PAGE_SIZE,
        )
    )
    posts = output.posts[:FEED_PAGE_SIZE]
    has_next = len(output.posts) > FEED_PAGE_SIZE
    context = {"posts": posts, "page": page, "has_next": has_next}
    if _is_htmx(request):
        return render(request, "web/partials/post_cards.html", context)
    return render(request, "web/feed.html", context)


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
