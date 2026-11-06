"""URL routes for the web UI (session-based)."""

from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("feed/", views.feed, name="feed"),
]
