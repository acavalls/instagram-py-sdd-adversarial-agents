"""URL configuration: admin, web UI and the REST API (routing per domain)."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.api_views import LoginAPIView, RegisterAPIView, TokenRefreshAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Web UI (session-based)
    path("web/", include("apps.web.urls")),
    # REST API (routing per domain; the API views live inside the apps)
    path("api/auth/register/", RegisterAPIView.as_view(), name="api-register"),
    path("api/auth/login/", LoginAPIView.as_view(), name="api-login"),
    # JWT refresh under the same /api/auth/ prefix as login (simplejwt's
    # TokenRefreshView wrapped in apps/accounts/api_views.py)
    path("api/auth/refresh/", TokenRefreshAPIView.as_view(), name="api-token-refresh"),
    # Posts API (patterns in task group 3, design decision 5)
    path("api/posts/", include("apps.posts.api_urls")),
    # OpenAPI schema and Swagger UI
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Media files in development so generated placeholder images render
# (MEDIA_URL/MEDIA_ROOT live in the shared settings).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
