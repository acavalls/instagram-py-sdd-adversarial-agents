"""DRF serializers for the posts capability (design decision 5).

The create serializer owns the request-side validation (caption limit and the
10-media maximum); the read serializers own the response shape (nested media,
``media_count``, ``first_image_url``). Business rules beyond field shape stay
in the use cases, per the layer discipline.
"""

from rest_framework import serializers

from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    CAPTION_TOO_LONG_ERROR,
    MEDIA_MAX_COUNT,
    MEDIA_TOO_MANY_ERROR,
    MediaType,
    Post,
    PostMedia,
)


class PostMediaSerializer(serializers.ModelSerializer):
    """One media entry of a post: order, media_type and its served URL."""

    url = serializers.ImageField(source="image", read_only=True)

    class Meta:
        model = PostMedia
        fields = ["order", "media_type", "url"]
        read_only_fields = fields


class PostReadSerializer(serializers.ModelSerializer):
    """Read shape for a single post: id, owner, caption and nested media."""

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    media = PostMediaSerializer(many=True, read_only=True)
    media_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "owner_username", "caption", "media", "media_count"]
        read_only_fields = fields

    def get_media_count(self, post: Post) -> int:
        # ``all()`` reuses the prefetch cache from the service layer, so this
        # never triggers an extra query per serialized post.
        return len(post.media.all())


class PostListSerializer(PostReadSerializer):
    """Read shape for the listing: adds the first image URL for thumbnails."""

    first_image_url = serializers.SerializerMethodField()

    class Meta(PostReadSerializer.Meta):
        fields = [*PostReadSerializer.Meta.fields, "first_image_url"]

    def get_first_image_url(self, post: Post) -> str | None:
        """URL of the first image media, or ``None`` for a media-less post."""
        first_media = next((m for m in post.media.all() if m.media_type == MediaType.IMAGE), None)
        if first_media is None:
            return None
        return first_media.image.url


class PostCreateSerializer(serializers.Serializer):
    """Create input: optional caption (<= 2200) and up to 10 images.

    The caption max-length message matches the model's
    ``CAPTION_TOO_LONG_ERROR`` so both paths report the same text (spec:
    Caption length limit). The 10-media maximum is enforced here (design
    decision 5), answering 400 with a validation error when exceeded.
    """

    caption = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=CAPTION_MAX_LENGTH,
        error_messages={"max_length": CAPTION_TOO_LONG_ERROR},
    )
    media = serializers.ListField(
        child=serializers.ImageField(),
        max_length=MEDIA_MAX_COUNT,
        required=False,
        error_messages={"max_length": MEDIA_TOO_MANY_ERROR},
    )

    def to_create_media_files(self) -> list | None:
        """The validated media list, as file-like objects for the use case."""
        media = self.validated_data.get("media")
        return media or None


class PostUpdateSerializer(serializers.Serializer):
    """Caption update input: caption is required and must not be blank."""

    caption = serializers.CharField(
        allow_blank=False,
        max_length=CAPTION_MAX_LENGTH,
        error_messages={"max_length": CAPTION_TOO_LONG_ERROR},
    )
