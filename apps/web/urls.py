from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("feed/", views.feed_view, name="feed"),
    path("register/", views.register_view, name="register"),
]
