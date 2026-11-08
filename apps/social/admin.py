from django.contrib import admin

from apps.social.models import Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    search_fields = ["follower__username", "following__username"]
    ordering = ["-created_at"]
