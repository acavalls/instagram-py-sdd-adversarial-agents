"""App configuration for the social domain."""

from django.apps import AppConfig


class SocialConfig(AppConfig):
    """Social app: follow relationships, feed and suggestions."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.social"
    label = "social"
