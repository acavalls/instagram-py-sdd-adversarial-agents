"""URL routes for the web UI (session-based)."""

from django.urls import include, path

from apps.web import social_views, story_views, views

app_name = "web"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("feed/", views.feed, name="feed"),
    # Web follow/unfollow HTMX buttons (social spec: Follow and unfollow
    # actions, design decision 6); routed by the target user's uuid.
    path("follow/<uuid:user_id>/", social_views.follow_user, name="follow-user"),
    path("unfollow/<uuid:user_id>/", social_views.unfollow_user, name="unfollow-user"),
    # Profile page (social spec: User profile page, design decisions 7 and 8).
    path("profile/<uuid:user_id>/", social_views.profile_view, name="profile"),
    # Following-list modal (social spec: Following list, design decision 9).
    path("profile/<uuid:user_id>/following/", social_views.following_list, name="following-list"),
    # Web stories (stories spec: Story creation, Story view tracking,
    # design decision 5); POST-only HTMX endpoints like the follow buttons.
    path("stories/create/", story_views.create_story, name="story-create"),
    path("stories/<uuid:story_id>/view/", story_views.view_story, name="story-view"),
    # Web post CRUD (patterns in task group 4, design decision 6)
    path("posts/", include("apps.posts.web_urls")),
]
