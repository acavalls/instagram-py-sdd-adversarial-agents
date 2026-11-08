from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User, validate_username


class UserCreateSerializer(serializers.Serializer):
    """Write serializer for registration: field-format validation only.

    Identity-duplicate rules are enforced by the registration use case
    through model validation, not here.
    """

    username = serializers.CharField(
        min_length=3,
        max_length=150,
        error_messages={
            "min_length": "Username must be at least 3 characters",
            "max_length": "Username must be 150 characters or fewer",
        },
    )
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        trim_whitespace=False,
        error_messages={"min_length": "Password must be at least 8 characters"},
    )

    def validate_username(self, value: str) -> str:
        try:
            validate_username(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class UserReadSerializer(serializers.ModelSerializer):
    """Read serializer for the created user data."""

    class Meta:
        model = User
        fields = ["id", "email", "username", "bio", "updated_at"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """Write serializer for API login.

    Blank or missing fields are accepted here on purpose: the login
    endpoint must answer 401 "Invalid credentials" for them, never a
    field-level 400. The use case reports the generic error.
    """

    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
        trim_whitespace=False,
    )
