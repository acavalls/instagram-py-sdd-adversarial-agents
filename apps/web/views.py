from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import validate_username
from apps.accounts.services import UserService
from apps.accounts.use_cases import (
    ERROR_INVALID_CREDENTIALS,
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)

REGISTER_SUCCESS_MESSAGE = "Account created successfully. Please login."
LOGIN_SUCCESS_MESSAGE = "Logged in successfully"
LOGOUT_SUCCESS_MESSAGE = "You have been logged out"
LOGIN_PAGE = "/web/login/"
FEED_PAGE = "/web/feed/"
ERROR_PASSWORD_TOO_SHORT = "Password must be at least 8 characters"
PASSWORD_MIN_LENGTH = 8


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
    """Landing page: declared placeholder empty state until the social capability lands."""
    return render(request, "web/feed.html")


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
