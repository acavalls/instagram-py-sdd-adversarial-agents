"""Web (HTMX) post routes (/web/posts/..., design decision 6).

Included from apps/web/urls.py so the post-specific views stay reachable
under the /web/posts/ prefix; the views live in apps/web/post_views.py.
"""

from django.urls import path

from apps.web import post_views

urlpatterns = [
    path("create/", post_views.create_post, name="post-create"),
    path("<uuid:pk>/edit-form/", post_views.edit_form, name="post-edit-form"),
    path("<uuid:pk>/cancel-edit/", post_views.cancel_edit, name="post-cancel-edit"),
    path("<uuid:pk>/submit-edit/", post_views.submit_edit, name="post-submit-edit"),
    path("<uuid:pk>/delete/", post_views.delete_post, name="post-delete"),
]
