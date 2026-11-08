import uuid

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.posts.models import PostMedia
from apps.posts.serializers import (
    PostCaptionUpdateSerializer,
    PostReadSerializer,
    PostWriteSerializer,
)
from apps.posts.services import PostMediaInput, PostService
from apps.posts.use_cases import (
    ERROR_POST_DELETE_FORBIDDEN,
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

ERROR_INVALID_PAGINATION = "Invalid pagination parameters"

ErrorSerializer = inline_serializer("PostError", {"error": serializers.CharField()})

OffsetParameter = OpenApiParameter(
    "offset", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Window start"
)
LimitParameter = OpenApiParameter(
    "limit", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Window size"
)


class PostListCreateView(APIView):
    """GET/POST /api/posts/ — list own posts (newest first) or create; 200/201/400."""

    permission_classes: list = [IsAuthenticated]

    @extend_schema(
        parameters=[LimitParameter, OffsetParameter],
        responses={200: PostReadSerializer(many=True), 400: ErrorSerializer},
    )
    def get(self, request: Request) -> Response:
        limit, offset, pagination_error = _parse_pagination(request.query_params)
        if pagination_error is not None:
            return Response({"error": pagination_error}, status=status.HTTP_400_BAD_REQUEST)
        output = ListPostsUseCase(PostService()).execute(
            ListPostsInput(user=request.user, limit=limit, offset=offset)
        )
        serializer = PostReadSerializer(output.posts, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=PostWriteSerializer,
        responses={201: PostReadSerializer, 400: ErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PostWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        output = CreatePostUseCase(PostService()).execute(
            CreatePostInput(
                user=request.user,
                caption=data.get("caption", ""),
                media=_media_inputs(data.get("media", [])),
            )
        )
        if not output.success or output.post is None:
            return Response({"error": output.error}, status=status.HTTP_400_BAD_REQUEST)
        response_serializer = PostReadSerializer(output.post, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """GET/PATCH/DELETE /api/posts/<uuid>/ — detail, caption update, deletion."""

    permission_classes: list = [IsAuthenticated]

    @extend_schema(responses={200: PostReadSerializer, 404: ErrorSerializer})
    def get(self, request: Request, post_id: uuid.UUID) -> Response:
        output = GetPostUseCase(PostService()).execute(
            GetPostInput(user=request.user, post_id=post_id)
        )
        if not output.success or output.post is None:
            return Response({"error": output.error}, status=status.HTTP_404_NOT_FOUND)
        serializer = PostReadSerializer(output.post, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=PostCaptionUpdateSerializer,
        responses={200: PostReadSerializer, 403: ErrorSerializer, 404: ErrorSerializer},
    )
    def patch(self, request: Request, post_id: uuid.UUID) -> Response:
        serializer = PostCaptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        output = UpdatePostUseCase(PostService()).execute(
            UpdatePostInput(
                user=request.user,
                post_id=post_id,
                caption=serializer.validated_data["caption"],
            )
        )
        if not output.success or output.post is None:
            return _error_response(output.error)
        response_serializer = PostReadSerializer(output.post, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={204: None, 403: ErrorSerializer, 404: ErrorSerializer},
    )
    def delete(self, request: Request, post_id: uuid.UUID) -> Response:
        output = DeletePostUseCase(PostService()).execute(
            DeletePostInput(user=request.user, post_id=post_id)
        )
        if not output.success:
            return _error_response(output.error)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _parse_pagination(query_params) -> tuple[int | None, int, str | None]:
    """Validate the limit/offset window; report an error for garbage values."""
    limit: int | None = None
    offset = 0
    try:
        raw_limit = query_params.get("limit")
        if raw_limit is not None:
            limit = int(raw_limit)
            if limit <= 0:
                raise ValueError
        raw_offset = query_params.get("offset")
        if raw_offset is not None:
            offset = int(raw_offset)
            if offset < 0:
                raise ValueError
    except ValueError:
        return None, 0, ERROR_INVALID_PAGINATION
    return limit, offset, None


def _media_inputs(files: list) -> tuple[PostMediaInput, ...]:
    """Map uploaded files to service inputs; the type comes from the content type."""
    return tuple(PostMediaInput(file=file, media_type=_media_type(file)) for file in files)


def _media_type(file: object) -> str:
    content_type = getattr(file, "content_type", "") or ""
    if content_type.startswith("video/"):
        return PostMedia.MediaType.VIDEO
    return PostMedia.MediaType.IMAGE


def _error_response(error: str | None) -> Response:
    """Map use-case error strings to 404 (unknown post) or 403 (ownership)."""
    if error == ERROR_POST_NOT_FOUND:
        status_code = status.HTTP_404_NOT_FOUND
    elif error in (ERROR_POST_EDIT_FORBIDDEN, ERROR_POST_DELETE_FORBIDDEN):
        status_code = status.HTTP_403_FORBIDDEN
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    return Response({"error": error}, status=status_code)
