"""DRF serializers for the accounts capability."""

from django.core.validators import RegexValidator
from rest_framework import serializers

from apps.accounts.models import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_TOO_SHORT_ERROR,
    USERNAME_FORMAT_ERROR,
    USERNAME_LENGTH_ERROR,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    User,
)

_USERNAME_REGEX = r"^[a-zA-Z0-9]+$"


class LoginSerializer(serializers.Serializer):
    """Login input serializer: username and password.

    No field-format rules here — wrong or unknown credentials are reported
    generically by the use case (design decision 6), so any shape of input is
    accepted and answered with the same "Invalid credentials" error.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserCreateSerializer(serializers.ModelSerializer):
    """Registration serializer: validates the input and serializes the user.

    Field-format rules (design decision 2): username 3-150 alphanumeric,
    valid email shape, password of at least 8 characters (write-only, never
    exposed in responses). Identity duplicates are NOT validated here — the
    use case reports them so the API view can answer 409.
    """

    username = serializers.CharField(
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        error_messages={"min_length": USERNAME_LENGTH_ERROR},
        validators=[RegexValidator(regex=_USERNAME_REGEX, message=USERNAME_FORMAT_ERROR)],
    )
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=128,
        error_messages={"min_length": PASSWORD_TOO_SHORT_ERROR},
    )

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "bio", "updated_at"]
        read_only_fields = ["id", "bio", "updated_at"]
