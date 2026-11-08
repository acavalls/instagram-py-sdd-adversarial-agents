from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("feed/", views.feed_view, name="feed"),
    path("register/", views.register_view, name="register"),
    path("posts/create/", views.create_post_view, name="create_post"),
    path("posts/<uuid:post_id>/card/", views.post_card_view, name="post_card"),
    path("posts/<uuid:post_id>/edit/", views.post_edit_view, name="post_edit"),
    path("posts/<uuid:post_id>/delete/", views.post_delete_view, name="post_delete"),
]
