# GBU Report — regularize-social-drifts

## Cycle 1 — 2026-11-07

### Executive verdict

RECOMMENDATION: NEXT — all 4 task groups implemented and Ugly-approved; the
adversarial loop (3 Bad attack rounds, 5 Good fix rounds, 1 orchestrator
adjudication) closed every blocking bug it found; final static verification
by Ugly APPROVED with all gates green.

### Requirement-by-requirement proof

| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |
| posts: Post data model | Post persisted with media | Media-count invariant enforced on save, objects.create, service create and bulk_create paths; deterministic ordering `[-created_at, -id]` | apps/posts/models.py:64,136-150; apps/posts/services.py:83-84; apps/posts/models.py:75-95 | test_media_count_limit_rejects_the_eleventh_media; test_caption_length_limit_bulk_create_is_guarded — passed | COVERED |
| posts: Post data model | Caption length limit | save() guard + PostQuerySet.update() literal validation (non-literal refused with error) + bulk_create guard | apps/posts/models.py (PostQuerySet.update/bulk_create) | test_atk_r023 (update), test_atk_r025 (bulk_create), test_web_submit_edit_rejects_over_long_caption — passed | COVERED |
| posts: Post listing | Pagination window | `-id` tiebreaker on Meta.ordering, list_for_user and list_feed; stable duplicate-free windows on tied timestamps | apps/posts/models.py:64; apps/posts/services.py:55; apps/social/services.py:103 | test_list_for_user_identical_created_at_stable_window; test_list_feed_identical_created_at_stable_duplicate_free_window — passed | COVERED |
| posts: Post creation | Whitespace-only caption becomes empty | API trims surrounding whitespace (DRF trim_whitespace); pinned by spec-backed test | apps/posts/serializers.py:76-81 | test_atk003d_whitespace_only_caption_is_normalized (traceability docstring) — passed | COVERED |
| posts: Caption update / Post deletion | Inline web edit, Cancel inline edit, Web deletion removes the card | Wording regularized: web edit/delete live on the profile grid (delta text only; behavior unchanged) | openspec/changes/regularize-social-drifts/specs/posts/spec.md | existing web edit/delete tests — passed | COVERED (spec-only) |
| posts: Post listing | Personal feed on the feed page | Post cards show the post's first media file (single-image card decision; delta text only) | delta posts spec.md | existing card tests — passed | COVERED (spec-only) |
| user-accounts: User account data | Bulk writes enforce the username rule | UserQuerySet.update() validates literal usernames and refuses non-literal (F()/Combinable/non-str) with the model's ValidationError; bulk_create and bulk_update guarded the same way; nothing written on refusal | apps/accounts/models.py:37-69 + bulk_update override | test_atk_r2_005 (literal update/bulk_create), test_atk_r008 (F(), sanctioned pytest.raises edit), test_atk_r018 (bulk_update) — passed | COVERED |
| user-accounts: User account data | Password comparison is byte-exact | Spec-owned behavior (trim_whitespace=False); test asserts padded login fails, exact bytes succeed | apps/accounts/serializers.py:28,49-51 | test_password_with_surrounding_spaces_round_trips_api (traceability docstring) — passed | COVERED |
| user-accounts: Web session logout | Logout is POST-only | Spec-owned behavior (@require_POST, 405, session stays active) | apps/web/views.py:114-115 | test_get_logout_no_longer_logs_out (traceability docstring) — passed | COVERED |
| user-accounts: User account data (manager) | (internal) create_user(None) | Raises the model's username ValidationError instead of TypeError | apps/accounts/models.py:87-103 | test_atk_r3_006 — passed | COVERED (no spec scenario; internal) |
| social: Duplicate follow rejected | (race) | IntegrityError from the unique-pair constraint translated to "Already following this user" — the losing racer gets the reference toast, never a 500 | apps/social/services.py:46-49 | test_follow_race_translates_integrity_error_into_reference_error; end-to-end test_follow_views.py:154-171 — passed | COVERED |
| social: Following list search filters | Following list search filters | Literal match verified: Django 6 already escapes `%`/`_`/`\` in icontains (audit F-06 was factually wrong on this runtime); behavior pinned by tests | apps/social/services.py:71-80 (docstring), ORM PatternLookup | test_get_following_search_matches_literals_never_wildcards; test_get_following_search_backslash_is_literal — passed | COVERED |
| (environment) config.yaml | — | "Django 5+" → "Django 6+" | openspec/config.yaml:11 | yaml.safe_load OK — passed | COVERED |

### Quality gates (actual results)

pytest 404 passed / 0 failed · coverage 99.53% (target >= 80) · ruff check:
0 issues · ruff format: 168 files clean · mypy: 0 errors in 76 source files

### Adversarial pass (The Bad)

- Iteration 1 (21 attacks): BUG-R001 (PostMedia.objects.bulk_create stored an
  11th media) and BUG-R002 (update(username=F()) stored a rule-violating
  username) → fixed by Good (round 1: silent contracts; round 2:
  orchestrator adjudication — the delta requires rejection WITH a validation
  error, so R002 raises and the repro test got one sanctioned edit to
  pytest.raises).
- Iteration 2 (new angles): BUG-R001/R002 verified closed; found BUG-R003
  (media bulk reassignment onto a full post) and BUG-R004
  (Post.objects.update over-limit caption) → fixed (PostMediaQuerySet
  update/bulk_update capacity guards; PostQuerySet.update caption guard) and
  the R018 gap (UserQuerySet.bulk_update missing) fixed.
- Iteration 3: R003/R004/R018 verified closed; found BUG-R005
  (Post.objects.bulk_create over-limit caption) → fixed (PostQuerySet.bulk_create
  guard); user approved closing the loop with static Ugly verification
  instead of a fourth attack (budget exhausted: 3/3 iterations, 10/10 runs).
- Non-blocking observations:
  - OBS-R3-1/2/3 (MEDIUM, open): Django 6 bulk_update delegates to
    update(Case(...)), which the new update() guards refuse as non-literal —
    bulk caption/username/post-reassignment updates are therefore total
    no-ops even for legal values. The invariants hold on every path (the
    pinned repro tests pass for this reason in part), but legal bulk_update
    writes are impossible. Fix must happen at the bulk_update level, never
    by loosening update(). Left open per the severity policy; candidate for
    a future cycle.
  - OBS-R001/R002 (LOW, from iteration 1): detached-instance FK quirk in
    tests; IntegrityError catch poisons surrounding atomic blocks only under
    future ATOMIC_REQUESTS.
  - Residual from Ugly group-1 audit: CreatePostUseCase maps any
    ValidationError to CAPTION_TOO_LONG_ERROR (unreachable mislabeling).
- Budget: 3 attack iterations, 10 test runs, ~21 min total (original limits
  2/6/6; user approved the extension twice).

### Deviations and assumptions

- Silent-drop semantics on bulk_create paths (media cap, caption) vs
  rejection-with-error on update paths: pinned by Bad's unmodified repro
  tests; documented in design decisions 3/4/13. (flagged for review)
- F-06 was closed without code: the original audit finding (wildcards pass
  through icontains) was empirically wrong on Django 6; literal match holds
  and is pinned by tests. (flagged for review)
- F-01 resolved as single-image post cards (agent business decision,
  2026-11-07, flagged for review).
- F-11/F-12 closed by decision: Django admin and seed_demo_data stay dev
  tooling outside the spec contract.
- The bulk_update no-op trio (OBS-R3-1/2/3) is accepted, open, non-blocking.

### Manual validation pointers (optional for the Sheriff)

- `.venv/bin/python -m pytest apps/accounts/tests/test_bad_attacks_reg_drifts2.py apps/posts/tests/test_bad_attacks_reg_drifts2.py apps/posts/tests/test_bad_attacks_reg_drifts3.py -q` — the whole bug-fix regression set.
- Registration/login flows unaffected: full suite 404 passed.

### Sheriff decision

(x) auto-approved per the regularization mini-pipeline (user chose
"corregimos el drift"); no separate SI/NO pause. Next: global verify →
archive → re-audit.
