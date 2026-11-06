"""App configuration for the posts domain."""

from django.apps import AppConfig


class PostsConfig(AppConfig):
    """Posts app: posts with media (models in task group 1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.posts"
    label = "posts"
