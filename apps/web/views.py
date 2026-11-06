"""Web UI views for registration and authentication (thin, design decision 5).

Field-format rules (password length, username format, email shape) are checked
here before calling the use case; identity-duplicate rules and authentication
live in the use cases and the model (design decisions 2 and 4).
"""

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.models import PASSWORD_MIN_LENGTH, PASSWORD_TOO_SHORT_ERROR, User
from apps.accounts.use_cases import (
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)

# The login view is implemented in a later task group; the literal keeps this
# group self-contained (it matches LOGIN_URL in the settings).
LOGIN_PAGE_URL = "/web/login/"
# The feed page belongs to a later change (posts/feed); for this change a
# minimal login-required placeholder view satisfies LOGIN_REDIRECT_URL and the
# "Protected pages require login" scenario.
FEED_PAGE_URL = "/web/feed/"

REGISTRATION_SUCCESS_TOAST = "Account created successfully. Please login."

LOGIN_SUCCESS_TOAST = "Logged in successfully"

LOGOUT_SUCCESS_TOAST = "You have been logged out"

# Same message the API path reports (DRF EmailField default, serializers.py)
# so both registration locations answer with identical wording.
EMAIL_FORMAT_ERROR = "Enter a valid email address."


def _check_field_formats(*, email: str, username: str, password: str) -> str | None:
    """Field-format rules checked before the use case (design decision 2)."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return PASSWORD_TOO_SHORT_ERROR
    try:
        validate_email(email)
    except ValidationError:
        return EMAIL_FORMAT_ERROR
    return User.validate_username_format(username)


def register(request: HttpRequest) -> HttpResponse:
    """Render the registration page and handle submissions with toasts."""
    context: dict[str, str] = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        error = _check_field_formats(email=email, username=username, password=password)
        if error is None:
            output = RegisterUserUseCase().execute(
                RegisterUserInput(username=username, email=email, password=password)
            )
            if output.success:
                messages.success(request, REGISTRATION_SUCCESS_TOAST)
                return redirect(LOGIN_PAGE_URL)
            assert output.error is not None  # a failed registration always has an error
            error = output.error
        messages.error(request, error)
        # Re-render with the submitted values so the visitor can correct them.
        context["username"] = username
        context["email"] = email
    return render(request, "web/register.html", context)


def login(request: HttpRequest) -> HttpResponse:
    """Render the login page and create the session on valid credentials."""
    context: dict[str, str] = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        output = AuthenticateUserUseCase().execute(
            AuthenticateUserInput(username=username, password=password)
        )
        if output.success:
            assert output.user is not None  # a successful authentication has a user
            auth_login(request, output.user)
            messages.success(request, LOGIN_SUCCESS_TOAST)
            return redirect(FEED_PAGE_URL)
        assert output.error is not None  # a failed authentication always has an error
        messages.error(request, output.error)
        # Re-render with the submitted username so the visitor can correct it;
        # the error is always the single generic message (never the cause).
        context["username"] = username
    return render(request, "web/login.html", context)


def logout(request: HttpRequest) -> HttpResponse:
    """Clear the session and redirect back to the login page with a toast."""
    auth_logout(request)
    messages.success(request, LOGOUT_SUCCESS_TOAST)
    return redirect(LOGIN_PAGE_URL)


@login_required
def feed(request: HttpRequest) -> HttpResponse:
    """Placeholder feed page (the real feed belongs to a later change)."""
    return render(request, "web/feed.html")
