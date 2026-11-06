# Tasks

## 1. Posts app scaffold and models

- [ ] 1.1 Create the `posts` app (`apps.py`, `__init__.py`), add it to `INSTALLED_APPS` and wire `/api/posts/` plus web post routes into `config/urls.py`; verify `manage.py check` passes
- [ ] 1.2 Implement `Post` and `PostMedia` models (UUID PKs, owner FK, caption, indexes, `can_edit`/`can_delete`) and create the initial migration; verify `manage.py makemigrations --check` and enable media serving in DEBUG
- [ ] 1.3 Write model tests for the "Post persisted with media" and "Caption length limit" scenarios in `apps/posts/tests/test_models.py`, named after the scenarios; verify they pass

## 2. Service and use cases

- [ ] 2.1 Implement `PostService` (`get_by_id` with select_related/prefetch, `list_for_user` with limit/offset, `exists`, `is_owner`, `create` with bulk media, `update_caption`, `delete`); verify service tests pass
- [ ] 2.2 Implement the five use cases (`CreatePost`, `ListPosts`, `GetPost`, `UpdatePost`, `DeletePost`) mirroring the success/error outputs; verify use case tests for success, "Post not found" and ownership errors pass

## 3. REST API

- [ ] 3.1 Implement the post serializers (create with caption ≤2200 and media ListField max 10, read with nested media, list with `first_image_url`) and `PostListCreateView` (`GET`/`POST /api/posts/`); verify tests for "Successful API creation", "API creation with too many media files", "API list of own posts", "No cross-user listing" and "Pagination window" pass
- [ ] 3.2 Implement `PostDetailView` (`GET`/`PATCH`/`DELETE /api/posts/<uuid>/` with 403/404 mapping); verify tests for "Existing post detail", "Unknown post detail", "Owner updates caption via API", "Non-owner update rejected", "Owner deletes post via API" and "Non-owner deletion rejected" pass

## 4. Web UI (HTMX)

- [ ] 4.1 Add htmx to `base.html` and implement `POST /web/posts/create/` with placeholder GIF generation and the "Post created!" toast; verify the "Successful web creation" test passes
- [ ] 4.2 Replace the feed placeholder with the personal feed: render the user's own posts as post cards with pagination; verify the "Personal feed on the feed page" test passes (web path)
- [ ] 4.3 Implement the inline caption edit HTMX flow (`edit-form`, `cancel-edit`, `submit-edit`) with the "Post updated!" toast; verify tests for "Inline web edit" and "Cancel inline edit" pass
- [ ] 4.4 Implement `POST /web/posts/<uuid>/delete/` removing the card with the "Post deleted!" toast; verify the "Web deletion removes the card" test passes

## 5. Integration checks

- [ ] 5.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green
- [ ] 5.2 Apply migrations to the dev database (`manage.py migrate`) and confirm the `/schema/` document includes the `/api/posts/` operations

## Workflow follow-up

- Archive the change after review; the delta spec becomes `openspec/specs/posts/spec.md` and the user-accounts landing requirement is updated.
- Verify the archived result with `openspec list --specs`.
