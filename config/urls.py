from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.api_views import LoginAPIView, RefreshAPIView, RegisterAPIView
from apps.posts.api_views import PostDetailView, PostListCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("web/", include("apps.web.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/register/", RegisterAPIView.as_view(), name="api-register"),
    path("api/auth/login/", LoginAPIView.as_view(), name="api-login"),
    path("api/auth/refresh/", RefreshAPIView.as_view(), name="api-refresh"),
    path("api/posts/", PostListCreateView.as_view(), name="api-posts"),
    path("api/posts/<uuid:post_id>/", PostDetailView.as_view(), name="api-post-detail"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
