from rest_framework import serializers

from apps.posts.models import (
    CAPTION_MAX_LENGTH,
    ERROR_MEDIA_LIMIT_EXCEEDED,
    MEDIA_LIMIT,
    Post,
    PostMedia,
)


class PostWriteSerializer(serializers.Serializer):
    """Write serializer for API post creation: field-level validation only.

    The caption limit and the media cap are enforced here as field
    validation for a clean 400; the storage-level rules live in the model
    and service below this layer.
    """

    caption = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=CAPTION_MAX_LENGTH,
        error_messages={
            "max_length": "Caption cannot exceed 2200 characters",
        },
    )
    media = serializers.ListField(
        child=serializers.FileField(),
        max_length=MEDIA_LIMIT,
        required=False,
        allow_empty=True,
        error_messages={
            "max_length": ERROR_MEDIA_LIMIT_EXCEEDED,
        },
    )


class PostCaptionUpdateSerializer(serializers.Serializer):
    """Write serializer for the caption update (PATCH)."""

    caption = serializers.CharField(
        required=True,
        allow_blank=True,
        max_length=CAPTION_MAX_LENGTH,
        error_messages={
            "max_length": "Caption cannot exceed 2200 characters",
        },
    )


class PostMediaReadSerializer(serializers.ModelSerializer):
    """Read serializer for one media file attached to a post."""

    class Meta:
        model = PostMedia
        fields = ["id", "order", "media_type", "file"]
        read_only_fields = fields


class PostReadSerializer(serializers.ModelSerializer):
    """Read serializer for post data, including nested media.

    `first_image_url` is the URL of the post's first image media
    (thumbnails), or the empty string when the post has no image media.
    """

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    media = PostMediaReadSerializer(many=True, read_only=True)
    media_count = serializers.SerializerMethodField()
    first_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "owner_username",
            "caption",
            "media",
            "media_count",
            "first_image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_media_count(self, post: Post) -> int:
        return post.media.all().count() if post.pk else 0

    def get_first_image_url(self, post: Post) -> str:
        for media in post.media.all():
            if media.media_type == PostMedia.MediaType.IMAGE:
                return self._absolute_media_url(media)
        return ""

    def _absolute_media_url(self, media: PostMedia) -> str:
        url = media.file.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url
