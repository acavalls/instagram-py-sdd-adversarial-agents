"""API views for the accounts capability (thin, per design decision 5)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.serializers import LoginSerializer, UserCreateSerializer
from apps.accounts.use_cases import (
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)


class RegisterAPIView(APIView):
    """POST /api/auth/register/ — create an account (201/400/409).

    Field validation failures answer 400 with field-level errors; duplicate
    email or username answer 409 with the corresponding error message.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=UserCreateSerializer, responses={201: UserCreateSerializer})
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        output = RegisterUserUseCase().execute(
            RegisterUserInput(
                username=serializer.validated_data["username"],
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        )
        if not output.success:
            return Response({"error": output.error}, status=status.HTTP_409_CONFLICT)
        assert output.user is not None  # a successful registration always creates a user
        return Response(UserCreateSerializer(output.user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """POST /api/auth/login/ — JWT login (200 with tokens / 401 generic error).

    Delegates credential checking to ``AuthenticateUserUseCase`` so the
    generic-error rule stays in the use case layer (design decision 6). On
    success the response carries the user data (mirroring the register
    response shape) plus an access/refresh token pair issued with
    ``RefreshToken.for_user`` (design decision 3).
    """

    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: UserCreateSerializer})
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        output = AuthenticateUserUseCase().execute(
            AuthenticateUserInput(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
        )
        if not output.success:
            return Response({"error": output.error}, status=status.HTTP_401_UNAUTHORIZED)
        assert output.user is not None  # a successful authentication always yields a user
        refresh = RefreshToken.for_user(output.user)
        return Response(
            {
                **UserCreateSerializer(output.user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshAPIView(TokenRefreshView):
    """POST /api/auth/refresh/ — exchange a valid refresh token for a new one.

    Thin wrapper over the simplejwt ``TokenRefreshView`` (design decision 3):
    200 with a new access token on success; a missing token answers 400 and
    an invalid/expired one 401, both without issuing any access token.
    """

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={200: TokenRefreshSerializer},
    )
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().post(request, *args, **kwargs)
