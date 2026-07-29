---
name: sdd-build
description: |
  Execution methodology for SDD Phase 3 (Build): turn a completed DESIGN into working,
  verified code. Covers KB-first knowledge resolution, task extraction from the file
  manifest, dependency ordering, specialist agent delegation (including the data
  engineering delegation map), per-file and full-run verification, recording autonomous
  decisions in the BUILD_REPORT, upstream status transitions, and the handoff to Phase 4.
  Use when asked to "execute the build", "implement from the design", or run "Phase 3"
  on a DESIGN_{FEATURE}.md. Not for creating the architecture itself — that is
  sdd-design — and not for archiving a finished feature — that is sdd-ship.
---

# SDD Build — Phase 3 Methodology

> The HOW of Phase 3: execute a completed DESIGN into working, verified code with
> on-the-fly task generation and specialist delegation. The executor is
> `build-agent` (`.claude/agents/workflow/build-agent.md`); its non-negotiable
> policies — decide-never-ask and halt-only-on-CRITICAL-risk — govern every step
> below and are not restated here.

---

## Knowledge Architecture — KB-First Resolution

Follow this resolution order before and during every task. It is mandatory, not optional.

```text
┌─────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE RESOLUTION ORDER                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DESIGN LOADING (source of truth for implementation)             │
│     └─ Read: .claude/sdd/features/DESIGN_{FEATURE}.md               │
│     └─ Extract: File manifest, code patterns, agent assignments     │
│     └─ Load KB domains specified in design                          │
│                                                                      │
│  2. KB PATTERN VALIDATION (before writing code)                     │
│     └─ Read: .claude/kb/{domain}/patterns/*.md → Verify patterns    │
│     └─ Compare: DESIGN patterns vs KB patterns → Ensure alignment   │
│                                                                      │
│  3. AGENT DELEGATION (for specialized files)                        │
│     ├─ @agent-name in manifest → Delegate via Task tool             │
│     └─ (general) in manifest   → Execute directly from patterns     │
│                                                                      │
│  4. CONFIDENCE ASSIGNMENT                                            │
│     ├─ KB pattern + agent specialist    → 0.95 → Execute            │
│     ├─ KB pattern + general execution   → 0.85 → Execute with care  │
│     ├─ No KB pattern + agent specialist → 0.80 → Agent handles      │
│     └─ No KB pattern + general          → 0.70 → Verify after       │
│                                                                      │
│  5. DECISION FORKS                                                   │
│     └─ Resolve under the executor's decide-never-ask policy and     │
│        record per "Recording Autonomous Decisions" below.           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Execution Loop

### Step 1: Load Context

```markdown
Read(.claude/sdd/features/DESIGN_{FEATURE}.md)
Read(.claude/sdd/features/DEFINE_{FEATURE}.md)
Read(CLAUDE.md)
```

Extract from the DESIGN: the file manifest, code patterns, agent assignments, and
the KB domains to load.

### Step 2: Extract Tasks from the File Manifest

**v2 manifest first (contract: `WORKFLOW_CONTRACTS.yaml` → `task_manifest`):**
when the DESIGN carries a `Task Manifest (v2)` section (`task_manifest` YAML,
`manifest_version: 2`), consume the declared tasks verbatim — NO inference.
The graph was validated at Design (`spec-lint --phase design`, TM.* rules);
execute tasks in topological order of `depends_on`, honor each task's
`owner`/`verification` commands, and record its `id` in the BUILD_REPORT
Task Execution table (the Task ID column). Dispatch remains sequential this
increment — `parallel_group` is declared data until the scheduling increment
lands.

**v1 fallback (no manifest):** convert the file manifest to a task list
on-the-fly, exactly as before, and record `manifest_version: 1` in the report
notes:

```markdown
From DESIGN file manifest:
| File | Action | Purpose |

Generate:
- [ ] Create/Modify {file1}
- [ ] Create/Modify {file2}
- [ ] ...
```

### Step 3: Order by Dependencies

Analyze imports and dependencies to determine execution order:
config first → utilities → handlers → tests.

```markdown
## Build Order

1. [ ] config.yaml (no dependencies)
2. [ ] utils.py (no dependencies)
3. [ ] main.py (depends on 1, 2)
4. [ ] test_main.py (depends on 3)
```

### Step 4: Execute Each Task

For each file, in order:

```text
┌─────────────────────────────────────────────────────┐
│                    EXECUTE TASK                      │
├─────────────────────────────────────────────────────┤
│  1. Read task from manifest                         │
│  2. Write code following DESIGN patterns            │
│     └─ Or delegate — see Delegation below           │
│  3. Run verification command                        │
│     └─ If FAIL → Fix and retry (max 3)             │
│  4. Mark task complete                              │
│  5. Move to next task                               │
└─────────────────────────────────────────────────────┘
```

Under `--tdd`, every code-bearing task runs its RED-GREEN cycle first — see
`--tdd mode` (after Step 5.5) — then this loop's verification.

Code standards for every file: no inline comments, type hints required,
self-documenting names, config in YAML over hardcoded values. Verify
incrementally — after each file, not only at the end. Fix forward: if something
breaks, fix it immediately. Keep each file independently functional.

### Step 5: Run Full Validation

After all files are created:

```bash
ruff check .        # lint
mypy .              # types (if configured)
pytest              # tests
```

Substitute the project's configured linter, type checker, and test runner when
it is not a Python project.

### Step 5.5: Whole-Branch Adversarial Review (mandatory)

Contract: `WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`.

After full validation passes, dispatch the review — never skip it, never
self-review instead:

1. Compute the branch scope: `BASE=$(git merge-base <default-branch> HEAD)`.
   If no merge-base is computable (no default branch, detached or unrelated
   history), fall back to reviewing every manifest file in full instead of
   a diff.
2. Dispatch `code-reviewer` via the Task tool with: the `BASE..HEAD` diff,
   the DEFINE's acceptance tests as the review lens, and the severity
   taxonomy Critical / Important / Minor.
3. Record the outcome in the BUILD_REPORT `## Review Verdict` section.

| Findings | Action |
|----------|--------|
| None | Verdict `clean` → Step 6 |
| Minor only | Record each; verdict `clean-with-minors` → Step 6 |
| Critical/Important | Fix loop (below) |

**Fix loop (budget 2 rounds, supervised and autonomous alike):** one round =
fix the findings → re-run the tests covering the amended code → scoped
re-review of the fix diff only. All findings resolved → verdict `clean` (or
`clean-with-minors`). Budget exhausted with open findings → verdict `dirty`,
open findings recorded as Blockers, recommend `/iterate`; under `/auto`,
Gate R (sdd-autopilot) maps this to abort-with-gap-report.

**Reviewer dispatch failure:** retry once; still failing → verdict `missing`
with a visible WARN — never an assumed `clean`. A `missing` verdict blocks
ship exactly like `dirty`.

**Build halted before the review:** a build that stops on a blocker before
Step 5.5 still writes the `## Review Verdict` section, verdict `missing`
(review not attempted) — the section is never omitted from a BUILD_REPORT.

### `--tdd` mode (opt-in flag on /build)

When invoked with `--tdd`, each code-bearing task follows RED-GREEN before
the standard per-file verification: write the failing test → run it and
observe the expected failure → write minimal code → run to green. Capture
the observed RED excerpt and the GREEN run summary per task in the
BUILD_REPORT `## TDD Evidence` section. Non-code tasks (markdown, YAML, templates) record `n/a (non-code
artifact)`. Without the flag, task execution is unchanged. The report Metadata
records the mode either way — `TDD Mode: opt-in` with the flag, `TDD Mode: off`
without it — and the contract gate (Step 6.5) requires the evidence section
whenever the mode is not `off`.

### Step 6: Generate the Build Report

Write `.claude/sdd/reports/BUILD_REPORT_{FEATURE}.md`. See Output Obligations.

Contract metadata rows (schema v2 — `build.report_contract`): every new report
records `Schema Version: 2` and `TDD Mode` in its Metadata table (`opt-in` when
the build ran with `--tdd`, `off` otherwise; `required` is reserved for
risk-driven TDD policy). A report without the Schema Version row is treated as
legacy by the contract gate below.

### Step 6.5: Contract Gate (mandatory)

Validate the report just written against the Build phase contract — artifact
`BUILD_REPORT_{FEATURE}.md`, phase `build`:

```bash
tools/spec-linter/spec-lint .claude/sdd/reports/BUILD_REPORT_{FEATURE}.md --phase build \
  --contracts-file .claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml
```

Run it as `tools/spec-linter/USAGE.md` documents, and act on the exit code
exactly as defined there:

| Exit | Action |
|------|--------|
| 0 | Proceed to Step 7. A WARN (e.g. a legacy report) is recorded VISIBLY in the report before proceeding |
| 1 | The build does NOT declare completion: fix the report — or the state it misreports — and re-lint once; still FAIL → Final Status `❌ BLOCKED`, open findings recorded as Blockers |
| >= 2 | Record a VISIBLE SKIP in the report and proceed — never assume PASS |

The exit-code contract and verdict semantics are owned by
`tools/spec-linter/USAGE.md` and the `contract_enforcement` block of
`.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`, which also declares this
phase's binding (`build.required_sections` + `build.report_contract` semantic
rules — verdict value, open blocking findings, fix-round budget, TDD evidence,
task completeness, legacy detection). Manual runs use the default
`--legacy-mode warn`; only Autopilot invokes `--legacy-mode fail` (Gate L
policy, sdd-autopilot). Ship re-runs this same validation before archiving.

### Step 7: Update Statuses and Hand Off

Apply the transitions in Status Transitions, then suggest the next phase per
Handoff.

---

## Delegation

### Decision flow

```text
Has @agent-name in manifest?
├─ YES → Delegate via Task tool
│        • Provide: file path, purpose, KB domains
│        • Include: code pattern from DESIGN
│        • Agent returns: completed file
│
└─ NO (general) → Execute directly
         • Use DESIGN patterns
         • Verify against KB
         • Handle errors locally
```

### Safety net — unresolvable `@agent` (specialist-autoprovision)

When a manifest `@agent-name` does not resolve against the router inventory at
delegation time (design→build drift), never fail on it and never fall back
silently: load `.claude/skills/specialist-autoprovision/SKILL.md` and run its
provisioning sub-flow. Delegation proceeds only after the new specialist's
citation verifies, or degrades to `(general)` + WARN per that skill's
degradation rules. The skill owns the methodology; this branch only invokes it.

### KB promotion on reuse (specialist-kb-bootstrap)

Before delegating to an agent, check each of its `kb_domains`: if the domain's
`index.md` opens with `> **Provenance**: auto-generated` and this run's
promotion budget is unspent (max 1 upgrade per run), append the `--validated`
upgrade (`kb-build`) as the run's FINAL task — best-effort: failure records
WARN, never a blocker. Budget spent, or further unvalidated domains → provenance
row `upgrade deferred — promotion budget spent`. All semantics — sensor, budget,
header flip, revert — are owned by
`.claude/skills/specialist-autoprovision/SKILL.md` (KB bootstrap section); this
branch only invokes them.

### Delegation protocol

1. Extract the agent name from the manifest
2. Build the delegation prompt with context
3. Invoke via Task tool
4. Receive the completed file
5. Write to disk and verify

````markdown
Task(
  subagent_type: "{agent-name}",
  description: "Create {file_path}",
  prompt: """
    Create file: {file_path}
    Purpose: {purpose from manifest}

    Code Pattern (from DESIGN):
    ```
    {code pattern}
    ```

    KB Domains: {domains from DEFINE}

    Requirements:
    - Follow the pattern exactly
    - Use type hints (Python)
    - No inline comments
    - Return complete file content
  """
)
````

### Data engineering delegation map

When the DESIGN contains pipeline architecture, dbt models, SQL files, DAGs, or
Spark jobs, delegate by file type:

| File Type | Delegate To |
|-----------|-------------|
| `models/**/*.sql` (dbt) | `dbt-specialist` |
| `dags/**/*.py` (Airflow) | `pipeline-architect` |
| `jobs/**/*.py` (PySpark) | `spark-engineer` |
| `contracts/**/*.yaml` | `data-contracts-engineer` |
| `tests/data/**/*.py` (GE) | `data-quality-analyst` |
| `schemas/**/*.sql` | `schema-designer` |

---

## Verification

### Standard verification (per file)

```bash
ruff check {file}
mypy {file}
pytest {test_file} -v
```

If a check fails: retry up to 3 times, then treat it as a blocker (see Error
Handling).

### Data engineering verification

Detect DE artifacts in the DESIGN (dbt models, SQL files, DAGs, Spark jobs) and
run the DE-specific verification tools:

```bash
# dbt models
dbt build --select {model_name}
dbt test --select {model_name}

# SQL linting
sqlfluff lint {sql_file} --dialect {dialect}
sqlfluff fix {sql_file} --dialect {dialect}

# Great Expectations
great_expectations suite run {suite_name}

# Spark (syntax check)
python -c "from pyspark.sql import SparkSession; exec(open('{file}').read())"
```

---

## Recording Autonomous Decisions

The decide-never-ask policy itself belongs to `build-agent`; this is the
recording mechanic that makes it auditable.

Every decision fork resolved without pausing — two valid interpretations, an
ambiguous policy, a gap the DESIGN did not pre-decide — gets one row in the
BUILD_REPORT `## Autonomous Decisions` table:

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|

- The rationale states why the choice is the safest / smallest-correct default,
  consistent with the DESIGN and the `.claude/kb/` patterns.
- The table is empty only if the DESIGN pre-decided everything.
- This is the post-run audit log that makes autonomous building reviewable —
  never omit a row to look decisive.

---

## Status Transitions

Contract obligation (`.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` →
`status_transitions`): the build MUST update upstream document statuses before
completing. A stale "Ready for Build" status after a completed build is a
contract violation.

| File | Field | Value |
|------|-------|-------|
| `DEFINE_{FEATURE}.md` | Status | `✅ Complete (Built)` |
| `DESIGN_{FEATURE}.md` | Status | `✅ Complete (Built)` |
| `DEFINE_{FEATURE}.md` | Next Step | `/ship` |
| `DESIGN_{FEATURE}.md` | Next Step | `/ship` |

---

## Output Obligations

| Artifact | Location |
|----------|----------|
| Code | As specified in the DESIGN file manifest |
| Build report | `.claude/sdd/reports/BUILD_REPORT_{FEATURE}.md` |

The report's shape is owned by `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`
— follow it, do not re-invent it. The sections this methodology feeds directly:
task execution with agent attribution (`@agent-name` vs `(direct)`),
verification results, and the Autonomous Decisions table.

---

## Handoff

When the build completes, suggest Phase 4:

```bash
/ship .claude/sdd/features/DEFINE_{FEATURE}.md
```

If the build stopped on blockers, recommend `/iterate` on the affected document
instead (see Error Handling).

---

## Quality Gate

Before declaring the build complete:

```text
PRE-FLIGHT CHECK
├─ [ ] All files from manifest created
├─ [ ] Each file verified (lint, types, tests)
├─ [ ] Full validation passes (lint, types, test suite)
├─ [ ] Whole-branch review dispatched; Review Verdict recorded (clean or clean-with-minors)
├─ [ ] Contract gate (Step 6.5): spec-lint --phase build exits 0, or a VISIBLE SKIP is recorded
├─ [ ] --tdd runs: TDD Evidence table filled for every code-bearing task
├─ [ ] No TODO comments left in code
├─ [ ] No hardcoded secrets or credentials
├─ [ ] Error cases handled
├─ [ ] Agent attribution recorded in BUILD_REPORT
├─ [ ] Autonomous Decisions table filled (or legitimately empty)
├─ [ ] DEFINE status updated to "✅ Complete (Built)"
├─ [ ] DESIGN status updated to "✅ Complete (Built)"
└─ [ ] BUILD_REPORT generated
```

---

## Anti-Patterns

| Never Do | Why | Instead |
|----------|-----|---------|
| Skip DESIGN loading | No patterns to follow | Always load DESIGN first |
| Improvise beyond DESIGN | Scope creep; files not in manifest | Follow patterns exactly |
| Ignore agent assignments | Lose specialization | Delegate as specified |
| Skip verification | Broken code ships | Verify every file, incrementally |
| Leave TODO comments | Incomplete code | Finish or escalate |
| Explain code with inline comments | Noise; code must self-document | Self-documenting names |

---

## Error Handling

A decision fork is not an error. This table covers genuine failures — code that
will not work, not a choice between valid options.

| Error Type | Action |
|------------|--------|
| Syntax error | Fix immediately, retry |
| Import error | Check dependencies, fix |
| Simple bug | Fix immediately and continue |
| Test failure | Debug and fix |
| Decision fork (two valid options) | Not a failure — decide and record per Recording Autonomous Decisions; never stop, never ask |
| Missing requirement (DEFINE gap — DESIGN cannot be executed) | Log a blocker in BUILD_REPORT; recommend `/iterate` on DEFINE — do not pause to ask |
| Architecture problem (DESIGN pattern is wrong) | Log a blocker in BUILD_REPORT; recommend `/iterate` on DESIGN — do not pause to ask |
| Blocker (build cannot complete after retries) | Stop, document all blockers in the report, recommend `/iterate` |

CRITICAL risks (secrets, irreversible deploy, data loss) are the executor's
territory: `build-agent` owns that halt policy, and this skill never overrides
it.

---

## References

- Executor + policies: `.claude/agents/workflow/build-agent.md`
- Entrypoint + flags: `.claude/commands/workflow/build.md`
- Report template: `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`
- Contracts: `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` (build block, `status_transitions`)
- Next phase: `.claude/commands/workflow/ship.md`
