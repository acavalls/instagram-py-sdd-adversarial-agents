# Agent Rules

## 0. Mandatory startup workflow

For EVERY request, before doing anything else:

1. Read `.opencode/context/workflow.md`.
2. Identify the current lifecycle stage from `openspec status`, the
   `tasks.md` checkboxes, and which changes are active vs archived.
3. Route the user's intent to the pipeline using the routing table in that
   file and execute the mapped phase.

The lifecycle runs as a PIPELINE with only two human decision points (the
manual-validation pause and the post-audit close/drift question). A request
that starts a cycle runs every automatic phase end-to-end, including the
automated commits at the agreed gates (see rule 2), and stops only at a
decision point or an error. Direct stage commands (e.g. "verify", "archive")
remain available to re-enter the pipeline mid-cycle.

This rule applies EVEN IF the user says "continue", "fix this", "small
change" or anything similar: identify the stage first.

## 1. Spec is the source of truth

Every observable behavior change MUST land as an OpenSpec change
(proposal + deltas) or be regularized as such. Behavior not described in
`openspec/specs/` is a defect, even if the code works. Never edit code to
introduce behavior that no change describes.

## 2. Automated commits at agreed gates

The agent MAY run `git add`, `git commit` and `git push`, but ONLY at the
gates agreed in `.opencode/context/workflow.md` (planning commit,
implementation commit, archive commit, and any regularization commits),
executing the super-commit procedure: inspect full repo state
(`git status`/`git diff`/`git log`), group changes into semantic commits
(feat/fix/test/chore/docs style, never mixing unrelated changes), commit
each group, then push. Never amend, never force push, never skip hooks,
never commit secrets. If the grouping is ambiguous or suspicious files
appear, stop and ask. Outside those gates, git write operations require an
explicit user request.

## 3. Language

All artifacts, specs, commits, documentation and code in English.

## 4. Reference implementation

The reference app lives at `/home/ale/mapfre/personal/django_ig`. Ground
requirements and designs in its real code (apps by domain: `accounts`,
`social`, `posts`, `api`, `web`; Clean Architecture layers:
views → use_cases → services → models). Never invent requirements the
reference app does not have without flagging the deviation.
