from typing import cast

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, Token

from apps.accounts.serializers import (
    LoginSerializer,
    UserCreateSerializer,
    UserReadSerializer,
)
from apps.accounts.services import UserService
from apps.accounts.use_cases import (
    ERROR_INVALID_CREDENTIALS,
    AuthenticateUserInput,
    AuthenticateUserUseCase,
    RegisterUserInput,
    RegisterUserUseCase,
)

ERROR_INVALID_REFRESH_TOKEN = "Invalid refresh token"

ErrorSerializer = inline_serializer("ErrorSerializer", {"error": serializers.CharField()})

RefreshRequestSerializer = inline_serializer(
    "RefreshRequestSerializer", {"refresh": serializers.CharField()}
)

RefreshResponseSerializer = inline_serializer(
    "RefreshResponseSerializer", {"access": serializers.CharField()}
)


class RegisterAPIView(APIView):
    """POST /api/auth/register/ — create an account; 201/400/409."""

    permission_classes: list = []

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserReadSerializer, 400: None, 409: ErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        use_case = RegisterUserUseCase(user_service=UserService())
        output = use_case.execute(
            RegisterUserInput(
                username=data["username"],
                email=data["email"],
                password=data["password"],
            )
        )
        if not output.success:
            return Response({"error": output.error}, status=status.HTTP_409_CONFLICT)
        return Response(UserReadSerializer(output.user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """POST /api/auth/login/ — issue JWT tokens; 200/401.

    Any failure, including blank or missing fields, answers the single
    generic error; field-level 400s are never produced.
    """

    permission_classes: list = []

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                "LoginResponseSerializer",
                {
                    "user": UserReadSerializer(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            ),
            401: ErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid()
        data = serializer.validated_data
        use_case = AuthenticateUserUseCase()
        output = use_case.execute(
            AuthenticateUserInput(
                username=data.get("username") or "",
                password=data.get("password") or "",
            )
        )
        if not output.success or output.user is None:
            return Response(
                {"error": ERROR_INVALID_CREDENTIALS}, status=status.HTTP_401_UNAUTHORIZED
            )
        refresh = RefreshToken.for_user(output.user)
        return Response(
            {
                "user": UserReadSerializer(output.user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class RefreshAPIView(APIView):
    """POST /api/auth/refresh/ — exchange a refresh token; 200/401.

    A missing, expired or invalid refresh token is rejected with 401
    without issuing a new access token.
    """

    permission_classes: list = []

    @extend_schema(
        request=RefreshRequestSerializer,
        responses={200: RefreshResponseSerializer, 401: ErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        token = request.data.get("refresh")
        if not isinstance(token, str) or not token:
            return self._rejected()
        try:
            refresh = RefreshToken(cast(Token, token))
        except TokenError:
            return self._rejected()
        return Response({"access": str(refresh.access_token)}, status=status.HTTP_200_OK)

    @staticmethod
    def _rejected() -> Response:
        return Response({"error": ERROR_INVALID_REFRESH_TOKEN}, status=status.HTTP_401_UNAUTHORIZED)
