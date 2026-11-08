from django.contrib import admin

from apps.posts.models import Post, Story


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["owner", "caption", "created_at"]
    search_fields = ["caption"]
    ordering = ["-created_at"]


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["owner", "created_at", "expires_at"]
    search_fields = ["owner__username"]
    ordering = ["-created_at"]
