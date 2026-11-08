# Anchored SDD Workflow

This is the project lifecycle. The agent MUST read this file at the start of
every request, identify the current stage (from `openspec status`, the
`tasks.md` checkboxes and the active vs archived changes), and route the
user's intent through the pipeline table below.

The lifecycle is a PIPELINE with exactly two human decision points:

- **PAUSE-1 (manual validation)**: after implementation. Question:
  "¿Te parece correcta la implementación? SI/NO".
- **PAUSE-2 (post-audit)**: only if the audit found drift. Question:
  "¿Cerramos el ciclo o corregimos el drift?".

Everything else runs automatically, including the commits at the agreed
gates via the super-commit procedure (see Conduct rules). A request that
starts a cycle executes every automatic phase end-to-end and stops only at
PAUSE-1, PAUSE-2, an error, or a GBU ESCALATION (see the GBU section).

## Intent routing

| What the user says | Action |
| --- | --- |
| Describes a new feature / "propon X" / "haz X" (no active cycle) | **Phase A** (propose → auto-decide ambiguities → validate → commit(plan) → apply → quality gates → commit(impl)) → **PAUSE-1** |
| "SI" (or equivalent approval at PAUSE-1) | **Phase B** (verify → archive → commit(archive)) → **Phase C** (audit) → close or **PAUSE-2** |
| "NO <explanation>" (rejection at PAUSE-1) | Decide from the explanation: `/opsx-update <change> <revision>` (artifacts wrong) or `/opsx-apply` (re-implementation) → quality gates → new commits (never amend) → **PAUSE-1** again |
| "cerramos" (post-audit, no drift or accepted drift) | Close the cycle with a final report |
| "corregimos" (post-audit, drift found) | Regularization mini-pipeline: `/opsx-propose` → apply → verify → archive → commit → audit again, until `IN SYNC` |
| "verify" / "archive" / "audit" / "implement[ group N]" | Direct re-entry into that stage (mid-cycle corrections) |
| "ambiguity X resolves to Y" / spec-level change of mechanism Z | `/opsx-update <change> <revision prompt>` |
| "review the implementation, X is missing" | `/opsx-update`, then `/opsx-apply` again, then quality gates and continue the pipeline |
| "change mechanism Z" (no artifact named) | Decision tree below |

### Decision tree for "change mechanism Z"

When the user asks to change a mechanism without naming an artifact, the
agent locates where the mechanism lives today and picks the path:

1. **Locate** the mechanism:
   - Active changes: `openspec list` + read the `proposal.md` and
     `tasks.md` of each active change.
   - Living specs: search `openspec/specs/**/spec.md`.
   - Archived history: search `openspec/changes/archive/`.

2. **Decide** by state:

   | Found in | Path |
   | --- | --- |
   | An active change (not archived) | **A**: `/opsx-update <change> <revision>` → re-apply affected tasks |
   | A living spec (archived) | **B**: `/opsx-propose` a new change with a `MODIFIED` delta → full pipeline |
   | Nowhere | `/opsx-propose` a new change: the user's information becomes new requirements |
   | Implemented but not archived, and the request changes the change's **intent** (not a refinement) | Say so and propose **B** (or a fresh change), instead of patching with A |

3. **Execute** that single stage, using the user's information (file,
   description, whatever provided) as the input of the revision, then stop
   and report.

Never assume when the state is ambiguous (e.g. two active changes touch the
same mechanism): ask the user before writing anything.

## Phases

### Phase A — plan and implement (automatic)

1. **Propose** (`/opsx-propose <change-name> <description>`):
   `openspec new change` → `openspec status --change <name> --json` →
   `openspec instructions <artifact> --change <name> --json` per artifact,
    grounded exclusively in this repository's OpenSpec artifacts and the
    requirements snapshots in `spec-ref/`. Delta spec format: `## Purpose`
    for new capabilities; `## ADDED/MODIFIED/REMOVED Requirements`;
    `### Requirement:` with MUST/SHALL; scenarios as `#### Scenario:` with
    WHEN/THEN bullets (exactly 4 hashtags); every requirement needs at least
    one scenario. If a capability depends on something not yet implemented,
    `design.md` must include a **dependency-wiring map**: the external
    dependencies per capability and the minimal placeholder wiring planned
    to keep each capability exercisable (the placeholder itself declared as
    a scenario in the delta spec).

2. **Ambiguities — auto-resolved, never delegated to the user.** The agent
   resolves every business decision itself, choosing the reasonable
   alternative (the requirements snapshots in `spec-ref/` are the default
   tie-breaker), and documents each decision in `design.md` (or
   `proposal.md`) as "Decision: ... (agent-decided, flagged for review)".
   The decisions are listed in the report so the user can overturn any of
   them later with `/opsx-update`. Do not pause for ambiguity questions.

3. **Validate**: `openspec validate <change-name>`.

4. **Commit gate (planning)** — super-commit (see Conduct rules), then push.

5. **Implementation — the GBU loop IS the apply** (`/opsx-apply`, all
   remaining task groups without stopping). The smallest implementation
   unit is a single task; never split a task. Per `config.yaml` operations
   guidance, run pytest and ruff after each task. The apply embeds the
   adversarial loop defined in the "GBU integration" section below:

   - Per task group: 🤠 Good implements the group → 👺 Ugly (fresh-context
     subagent) audits the group against its delta-spec scenarios AND for
     exercisability: if a capability the group introduces is not exercisable
     end-to-end through the primary interface its delta spec declares
     (web UI path, API call, command invocation), the verdict is REJECTED
     even when all tests pass.
     - APPROVED → next group.
     - REJECTED → Good fixes exactly the required actions (iteration ≤ 3)
       → re-audit.
     - ESCALATION → STOP and ask the user.
   - After the last group: 🌵 Bad attacks the whole change surface once
     (budget in `gbu-state.json`).
     - SURVIVES → apply done.
     - BROKEN (only blocking bugs: severity CRITICAL/HIGH violating a
       delta/living-spec requirement, per the Severity policy in
       `bad.md`) → Good fixes the bugs (iteration ≤ 3) → Bad re-attacks.
     - Non-blocking findings (severity MEDIUM and below) never trigger a
       fix loop: they are recorded in `gbu-report.md` as observations.
     - ESCALATION or BUDGET_EXHAUSTED → STOP and ask the user.
   - Update `gbu-state.json` after every step (resume capability).
   - Finish with the full quality gates: pytest (all pass), coverage >=
     80%, ruff, mypy.

6. **Commit gate (implementation)** — super-commit, then push.

7. **PAUSE-1**: generate `openspec/changes/<change>/gbu-report.md`
   (format in the GBU section) — the evidence artifact that shows why the
    implementation is correct, self-sufficient for a reader who does not
    look at the code. Report what was implemented (artifacts, tests, gates,
    adversarial pass) and ask: "¿Te parece correcta la implementación?
    SI/NO". The Sheriff decides from the report, and may still validate
    manually — the manual validation pointers are mandatory whenever the
    change declares an interface (click path for the web UI, curl example
    for REST, command invocation for CLI), including expected results and
    the expected state of any placeholder wiring.

### Phase B — verify and archive (automatic, after "SI")

8. **Verify** (`/opsx-verify`): a single 👺 Ugly agent with fresh context
   compares the whole implementation against the deltas: completeness,
   requirement mapping, scenario coverage, design adherence. The
   `gbu-report.md` is direct input for it (which risks were already
   attacked, which bugs already closed). CRITICAL issues loop back to
   `/opsx-update` + `/opsx-apply` + new commits before archiving.

9. **Archive** (`/opsx-archive`): sync the delta into the living spec, move
   the change to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

10. **Commit gate (archive)** — super-commit, then push. Audit (Phase C)
    must run on a clean tree because it uses `git log` as evidence.

### Phase C — audit and close (automatic, with PAUSE-2 on drift)

11. **Audit** (skill `spec-audit`).

    - `IN SYNC` → close the cycle with a final report. Done.
    - Drift found → **PAUSE-2**: report the findings and ask
      "¿Cerramos el ciclo o corregimos el drift?".
      - "corregimos" → regularization mini-pipeline (propose → apply →
        verify → archive → super-commit) → audit again, repeat until
        `IN SYNC`.
      - "cerramos" → close with the findings documented for a future cycle.

## GBU integration (the apply loop)

The GBU (Good, Bad, Ugly) pattern turns apply into an adversarial loop with
fresh-context subagents (`task()` is the primitive; there is no new
user-facing command). The main agent is the orchestrator: it reads each
subagent's JSON, decides the next step, and re-prompts with feedback.

### Agents

| Agent | File | Mode | Writes | Returns |
|---|---|---|---|---|
| 🤠 Good | `.opencode/agents/good.md` | generator | workspace code + tests + `tasks.md` checkboxes | JSON summary (plan, files, tests, assumptions, validation) |
| 👺 Ugly | `.opencode/agents/ugly.md` | auditor (read-only) | nothing | JSON `APPROVED / REJECTED / ESCALATION` with per-scenario evidence |
| 🌵 Bad | `.opencode/agents/bad.md` | adversarial validator | only NEW test files in test dirs | JSON `SURVIVES / BROKEN / BUDGET_EXHAUSTED / ESCALATION` with structured bugs |

All three are generic (no language/framework assumptions); the project
specialization comes from `AGENTS.md` and the project skills each agent is
instructed to load. Their spec is the change's delta specs + living specs;
their contract is `openspec/config.yaml` + the change's `design.md`. Agent
permissions are declared per project in `opencode.json`
(`agent.<name>.permission`), keeping the agent files copyable to other
projects: `ugly` is read-only (`edit: deny` plus the project's read-only
tooling allowlist), `bad` may write only new test files (destructive and
git-writing bash commands are denied), `good` has full write access.

### State and budgets

- **State file**: `openspec/changes/<change>/gbu-state.json`, updated after
  every step. Fields: change, status, current group/iteration, per-agent
  status/output/iterations, budget config, budget usage, log. If a session
  dies mid-apply, the next session reads the state and continues from the
  pending group — it never restarts from zero. The file is archived with
  the change.
- **Budgets** (defaults; adjustable in `gbu-state.json`, to be calibrated
  after the first real project):
  - Good↔Ugly per group: max **3** iterations.
  - Bad attack iterations: max **2**.
  - Bad wall clock: **6 minutes** per cycle.
  - Bad test-runner executions: **6** targeted runs (never full suites —
    full suites belong to the quality gates). EVERY test-runner execution
    counts toward this budget, including targeted inspection runs;
    overruns are reported honestly in the report and the budget line.
  - Any budget exhausted before delivering evidence is reported as
    `BUDGET_EXHAUSTED` → STOP and ask the user (never treated as "code is
    correct"). Exception: when the budget is exhausted before all groups
    are attacked, the declared practice is to finish the remaining
    verification as the orchestrator (full suite plus Ugly static checks)
    and record the substitution honestly in the report and the state log.

### Orchestrator duties

- Invoke each agent with a fresh context; parse and validate the JSON
  (invalid output → retry once, then treat as ESCALATION).
- Update `gbu-state.json` and append to `gbu-report.md` after every step.
- After each Bad pass, review its diff (`git status --short` /
  `git diff`): the Bad may only ADD new test files under test directories.
  Anything else → revert it, discard that pass, and re-run (count the
  iteration).
- The loop self-corrects within budget without stopping for the user;
  it stops ONLY on ESCALATION, BUDGET_EXHAUSTED, and at commit gates.

### Report (`gbu-report.md`)

One report per change: `openspec/changes/<change>/gbu-report.md`. It is
the Sheriff's decision artifact: evidence, not an audit trail. It must be
self-sufficient to convince a human who does not read the code (who may
still validate manually — include pointers for that). Append-only across
cycles: each apply cycle appends a `## Cycle N` section; the report is
archived with the change.

```markdown
# GBU Report — <change>

## Cycle N — <date>

### Executive verdict
RECOMMENDATION: NEXT / UPDATE / ESCALATE — <one sentence why>

### Requirement-by-requirement proof
| Requirement | Scenario | How it is solved (plain language) | Evidence (file:line) | Test proving it (name, result) | Ugly verdict |
| --- | --- | --- | --- | --- | --- |

### Quality gates (actual results)
pytest N/N passed · coverage N% (target >= 80) · ruff: 0 issues · mypy: 0 errors

### Adversarial pass (The Bad)
- ATK-001 <attack> → survived / bug BUG-00N found → fixed → regression
  test <name> added to the suite
- Non-blocking observations: <one-line MEDIUM findings with repro, or
  "none">
- Budget: X min used, Y test runs (limits: 6 min, 6 runs, 2 iterations)

### Deviations and assumptions
<each documented by Good, with impact>

### Manual validation pointers (mandatory when the change declares an interface)
<executable validation script per declared interface: click path for the
web UI, curl example for REST, command invocation for CLI — each with the
expected result and the expected state of any placeholder wiring; omit only
if the change declares no human-exercisable surface>

### Sheriff decision
[ ] SI — proceed to verify/archive
[ ] NO — <reason> → /opsx-update (artifacts wrong) or re-apply
```

Consumers: the Sheriff (decides SI/NO at PAUSE-1), the stage 7.B Ugly
(direct input for the global verify), and the archive (decision history).

## Super-commit procedure (used at every commit gate)

1. Inspect the full repo state: `git status --short`, `git diff --stat`,
   `git log --oneline -10`.
2. Group changes by intent (feat/fix/refactor/test/chore/docs/config);
   never mix unrelated changes in one commit.
3. Check for secrets or suspicious files (.env, credentials, keys); if any
   appear, stop and ask before committing.
4. `git add <files>` per group, commit each group with a semantic message
   following the repo style, then `git push`.
5. Never amend, never force push, never skip hooks. If the grouping is
   genuinely ambiguous, stop and ask.

## Conduct rules

- Commits and pushes run automatically at the agreed gates only
  (planning, implementation, archive, regularization), via the
  super-commit procedure. Any git write outside those gates requires an
  explicit user request.
- The spec is the source of truth: every observable behavior change lands as
  an OpenSpec change; behavior not described in `openspec/specs/` is a
  defect.
- **Exercisable-surface rule**: every change must leave the system in a state
  where each new capability is exercisable end-to-end through the primary
  interface its delta spec declares (web UI path, API call, command
  invocation, ...), by a human who does not read code or touch the
  database. A capability that is not exercisable through its declared
  interface is a defect, regularizable via the post-audit mini-pipeline.
- **Minimal wiring**: when a capability depends on something not yet
  implemented, the change must build the minimal wiring needed to keep it
  exercisable (placeholder navigation entry, stub endpoint, mock), and the
  placeholder MUST be declared as a scenario in the delta spec. Silent
  untracked wiring is a defect; replacing a placeholder later is an
  observable change that requires its own delta.
- All artifacts, specs, commits and documentation in English.
- Spec-driven inputs only (AGENTS.md rule 4): propose and apply read
  exclusively this repository's OpenSpec artifacts, `openspec/config.yaml`,
  the requirements snapshots in `spec-ref/` and the project skills in
  `.opencode/skills/`. NEVER read implementation code from outside this
  repository; if something seems to require it, stop and ask the user.
