"""REST API routes for the posts domain (/api/posts/, design decision 5).

The include is wired from the scaffold in ``config/urls.py``.
"""

from django.urls import path

from apps.posts.api_views import PostDetailView, PostListCreateView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="api-post-list-create"),
    path("<uuid:pk>/", PostDetailView.as_view(), name="api-post-detail"),
]
