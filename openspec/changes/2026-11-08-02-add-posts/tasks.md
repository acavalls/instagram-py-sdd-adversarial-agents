# Tasks

Ordering premise: inside-out WITHIN each task (model → service → use case →
adapter); each group is validation-closed, with its Manual validation line.

## 1. Posts app and models (Requirement: Post data model)

- [x] 1.1 Create the `posts` app, add it to `INSTALLED_APPS` and wire `/api/posts/` plus the web post routes into the URL config; verify `manage.py check` passes and enable media serving in DEBUG
- [x] 1.2 Implement `Post` and `PostMedia` models (UUID PKs, owner FK, caption ≤ 2200 with model-level enforcement on save and bulk paths, up to 10 ordered media with type and zero-based order, deterministic newest-first ordering) and create the initial migration; verify `manage.py makemigrations --check` and model tests for persistence, caption/media limits and bulk-path refusals pass

  - Manual validation: `manage.py makemigrations --check` clean; dev server
    boots.

## 2. Services and use cases (Requirements: Post creation, Post listing, Post detail, Caption update, Post deletion, Post visibility)

- [x] 2.1 Implement `PostService` (`get_by_id` with select_related/prefetch, `list_for_user` with limit/offset, `exists`, `is_owner`, `create` with bulk media, `update_caption`, `delete`); verify service tests pass
- [x] 2.2 Implement the five use cases (`CreatePost`, `ListPosts`, `GetPost`, `UpdatePost`, `DeletePost`) mirroring the success/error outputs; verify use case tests for success, "Post not found" and ownership errors pass

  - Manual validation: run the posts service/use-case tests by scenario
    name (no UI surface yet — this group introduces no user-exercisable
    capability on its own).

## 3. REST API surface (Requirements: Post creation, Post listing, Post detail, Caption update, Post deletion, Post visibility; api-docs MODIFIED)

- [x] 3.1 Implement the post serializers (create with caption ≤ 2200, whitespace trimming and media ListField max 10; read with nested media and `first_image_url`) and `PostListCreateView` (`GET`/`POST /api/posts/`); verify tests for "Successful API creation", "API creation with too many media files", "API list of own posts", "API list includes first image thumbnail", "Whitespace-only caption becomes empty", "No cross-user listing" and "Pagination window" pass
- [x] 3.2 Implement `PostDetailView` (`GET`/`PATCH`/`DELETE /api/posts/<uuid>/` with 403/404 mapping); verify tests for "Existing post detail", "Unknown post detail", "Owner updates caption via API", "Non-owner update rejected", "Owner deletes post via API" and "Non-owner deletion rejected" pass
- [x] 3.3 Verify `/schema/?format=json` now includes the posts paths and `/docs/` lists them (MODIFIED api-docs scenarios)

  - Manual validation: with a JWT from `/api/auth/login/`, `curl` a post
    creation (`POST /api/posts/`), list it (`GET /api/posts/`), fetch its
    detail, patch the caption and delete it (204); open `/docs/` and see
    the posts operations.

## 4. Web surface: create, personal feed, edit, delete (Requirements: Post creation web, Post listing web, Caption update web, Post deletion web; web-ui MODIFIED + ADDED)

- [x] 4.1 Wire the sidebar Create entry to `POST /web/posts/create/` with placeholder GIF generation and the "Post created!" toast (MODIFIED web-ui "Sidebar navigation": "Create submits the post creation form"); verify the scenario test passes
- [x] 4.2 Replace the landing placeholder content with the personal feed: own posts as post cards (card anatomy, HTMX scroll sentinel, end marker) with pagination; verify tests for "Personal feed on the feed page", "Home feed loads more posts on scroll" and "Non-HTMX request with a page parameter renders the full page" pass
- [x] 4.3 Implement the post card template per the ADDED "Post card anatomy" (owner header, media or placeholder icon, actions row placeholders, caption + relative time, owner edit/delete menu, first-media-only); verify the card anatomy scenario tests pass
- [x] 4.4 Implement the inline caption edit HTMX flow (edit form, cancel, submit) and `POST /web/posts/<uuid>/delete/` removing the card; verify tests for "Inline web edit", "Cancel inline edit" and "Web deletion removes the card" pass

  - Manual validation: log in → click Create in the sidebar → see "Post
    created!" and the new card in the home feed; scroll to load more;
    edit the caption inline (toast "Post updated!"), cancel an edit;
    delete the post (card disappears, toast "Post deleted!").

## 5. Quality gates

- [x] 5.1 Run the full suite: `pytest` with coverage >= 80%, `ruff check` and `ruff format --check`, `mypy` — all green
- [x] 5.2 Apply migrations to the dev database and confirm the schema/docs surface shows the posts operations

## Workflow follow-up

- Archive the change after review; the deltas merge into
  `openspec/specs/{posts,web-ui,api-docs}/spec.md`.
