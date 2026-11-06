"""API views for the posts capability (thin, per design decision 5).

Views only validate request shape, call the use cases and map their
success/error outputs to HTTP codes: 400 for serializer validation errors,
403 when an ownership error (message contains "own") is returned, 404 for
"Post not found". Business rules live in the use case/service layers.
"""

import uuid
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.posts.serializers import (
    PostCreateSerializer,
    PostListSerializer,
    PostReadSerializer,
    PostUpdateSerializer,
)
from apps.posts.use_cases import (
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

# Sane pagination defaults for GET /api/posts/ (documented in the schema).
DEFAULT_LIMIT = 10
DEFAULT_OFFSET = 0


def _error_response(error: str) -> Response:
    """Map a use case error to 403 (ownership, message contains "own") or
    404 (unknown post), with the error as the response body (design
    decision 5)."""
    status_code = status.HTTP_403_FORBIDDEN if "own" in error else status.HTTP_404_NOT_FOUND
    return Response({"error": error}, status=status_code)


def _parse_pagination(query_params: Any) -> tuple[int, int] | None:
    """Parse limit/offset query params with sane defaults.

    Returns ``(limit, offset)``, or ``None`` when either value is not a
    non-negative integer (the caller then answers 400).
    """
    limit = query_params.get("limit", DEFAULT_LIMIT)
    offset = query_params.get("offset", DEFAULT_OFFSET)
    try:
        limit_value = int(limit)
        offset_value = int(offset)
    except (TypeError, ValueError):
        return None
    if limit_value < 0 or offset_value < 0:
        return None
    return limit_value, offset_value


class PostListCreateView(APIView):
    """GET/POST /api/posts/ — list the authenticated user's own posts or
    create one (201 on success).

    GET supports limit/offset pagination (defaults 10/0); POST accepts an
    optional caption (max 2200) and up to 10 media images.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int, OpenApiParameter.QUERY, default=DEFAULT_LIMIT),
            OpenApiParameter("offset", int, OpenApiParameter.QUERY, default=DEFAULT_OFFSET),
        ],
        responses={200: PostListSerializer(many=True)},
    )
    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        pagination = _parse_pagination(request.query_params)
        if pagination is None:
            return Response(
                {"error": "limit and offset must be non-negative integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit, offset = pagination
        output = ListPostsUseCase().execute(
            ListPostsInput(user=request.user, limit=limit, offset=offset)
        )
        return Response(PostListSerializer(output.posts, many=True).data)

    @extend_schema(
        request=PostCreateSerializer,
        responses={201: PostReadSerializer},
    )
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        output = CreatePostUseCase().execute(
            CreatePostInput(
                owner=request.user,
                caption=serializer.validated_data.get("caption", ""),
                media_files=serializer.to_create_media_files(),
            )
        )
        if not output.success:
            # Only the caption limit can still fail after serializer
            # validation (belt and braces for non-standard input paths).
            return Response({"error": output.error}, status=status.HTTP_400_BAD_REQUEST)
        assert output.post is not None  # a successful creation always yields a post
        return Response(PostReadSerializer(output.post).data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """GET/PATCH/DELETE /api/posts/<uuid>/ — retrieve, update the caption or
    delete a post, enforcing ownership via the use cases.

    Unknown identifier or non-owner GET → 404 {"error": "Post not found"};
    a non-owner PATCH/DELETE → 403 with the model's ownership error message.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PostReadSerializer})
    def get(self, request: Request, pk: uuid.UUID, *args: object, **kwargs: object) -> Response:
        output = GetPostUseCase().execute(GetPostInput(post_id=pk, user=request.user))
        if not output.success:
            assert output.error is not None  # a failed use case always reports an error
            return _error_response(output.error)
        assert output.post is not None  # a successful retrieval always yields a post
        return Response(PostReadSerializer(output.post).data)

    @extend_schema(
        request=PostUpdateSerializer,
        responses={200: PostReadSerializer},
    )
    def patch(self, request: Request, pk: uuid.UUID, *args: object, **kwargs: object) -> Response:
        serializer = PostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        output = UpdatePostUseCase().execute(
            UpdatePostInput(
                post_id=pk,
                user=request.user,
                caption=serializer.validated_data["caption"],
            )
        )
        if not output.success:
            assert output.error is not None  # a failed use case always reports an error
            return _error_response(output.error)
        assert output.post is not None  # a successful update always yields a post
        return Response(PostReadSerializer(output.post).data)

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: uuid.UUID, *args: object, **kwargs: object) -> Response:
        output = DeletePostUseCase().execute(DeletePostInput(post_id=pk, user=request.user))
        if not output.success:
            assert output.error is not None  # a failed use case always reports an error
            return _error_response(output.error)
        return Response(status=status.HTTP_204_NO_CONTENT)
