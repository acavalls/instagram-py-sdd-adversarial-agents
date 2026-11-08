from django.urls import path

from apps.web import story_views, views

app_name = "web"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("feed/", views.feed_view, name="feed"),
    path("profile/<uuid:user_id>/", views.profile_view, name="profile"),
    path("profile/<uuid:user_id>/follow/", views.follow_user_view, name="follow"),
    path("profile/<uuid:user_id>/unfollow/", views.unfollow_user_view, name="unfollow"),
    path("profile/<uuid:user_id>/following/", views.following_list_view, name="following_list"),
    path("register/", views.register_view, name="register"),
    path("posts/create/", views.create_post_view, name="create_post"),
    path("posts/<uuid:post_id>/card/", views.post_card_view, name="post_card"),
    path("posts/<uuid:post_id>/edit/", views.post_edit_view, name="post_edit"),
    path("posts/<uuid:post_id>/delete/", views.post_delete_view, name="post_delete"),
    path("stories/create/", story_views.create_story_view, name="create_story"),
    path("stories/<uuid:story_id>/view/", story_views.view_story_view, name="view_story"),
]
