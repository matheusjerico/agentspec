# DESIGN: Commit Parallel Policy

> Technical design: a `commit_parallel` contract block (commit rules + parallel preconditions as data), per-task commit and parallel-dispatch conduct in sdd-build, the report's Commit column, and the autopilot composition note. Zero linter changes.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMMIT_PARALLEL_POLICY |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_COMMIT_PARALLEL_POLICY.md](./DEFINE_COMMIT_PARALLEL_POLICY.md) |
| **Risk Level** | low (echo from DEFINE — conduct + data + one column; no gate semantics change) |
| **Status** | Ready for Build |
| **Design Confidence** | 0.92 — pure conduct/data increment on stable surfaces |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│         COMMIT & PARALLELISM POLICY — SYSTEM DIAGRAM                  │
├──────────────────────────────────────────────────────────────────────┤
│  Per task (after verification + Step 4.6 review):                    │
│    commit THIS task's files with execution.commit (Conventional);    │
│    record short SHA in the Task Execution Commit column;             │
│    no Git → `unavailable` (never a blocker);                         │
│    v1/session-scoped work → `session` with justification             │
│                                                                      │
│  Commit rules (data): never mix independent tasks · never commit     │
│  failing tests (except a marked RED commit) · never rewrite history  │
│  without authorization · squash/rebase = maintainer's decision       │
│                                                                      │
│  Parallel dispatch (activates Increment-3 parallel_group):           │
│    dispatch same-group tasks concurrently ONLY when ALL hold:        │
│      deps complete · write-sets disjoint (TM-validated at Design) ·  │
│      no shared migration/contract in dispute · agent budget allows · │
│      merge strategy defined                                          │
│    any conflict or precondition failure → SERIALIZE (never           │
│    auto-merge risky work)                                            │
│                                                                      │
│  /auto: task commits compose with phase checkpoint commits;          │
│  dispatch respects the run's agent budget. No linter rule changes.   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `commit_parallel` contract block | 5 commit rules, 5 parallel preconditions, fallback vocabulary (v3.14.0) | YAML |
| sdd-build conduct | Step 4.9 (per-task commit) + dispatch policy paragraph in Step 2's v2 branch | Skill markdown |
| Report Commit column | Task Execution gains `Commit` (sha / unavailable / session) | Template |
| Autopilot note | Composition of task commits with checkpoint commits; budget respect | Skill markdown |

---

## Key Decisions

### Decision 1: Zero linter changes — conduct + data only `[ASSUMED 0.95]`
The graph sensors that make parallelism safe (TM.write_conflict, TM.cycle) already run at Design; enforcing commit linkage in the report contract is deferred until adoption exists (DEFINE Out of Scope). This increment's deterministic surface is documental tests over the block, skills, and template.

### Decision 2: Commit vocabulary `sha / unavailable / session` `[ASSUMED 0.90]`
`session` (with justification in Notes) covers v1 builds and environments where per-task commits are impractical — honest recording beats forced granularity (§13.1 "não exigir um commit por arquivo" generalized).

### Decision 3: Parallel dispatch trusts Design-time validation; runtime conflicts serialize `[ASSUMED 0.88]`
No runtime locking (DEFINE A-002): declared write-sets were validated disjoint; an out-of-declaration collision is a conduct violation handled by serializing the remainder of the group. Safe because dispatch is opt-in per group and the branch review sees the integrated result.

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: commit_parallel block + v3.14.0 history
      requirements: [REQ-001, REQ-006]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: contract, commit: "feat(sdd): commit_parallel contract data" }
      acceptance: ["yaml.safe_load exposes commit_parallel"]
      verification:
        green: "python3 -c 'import yaml; yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"commit_parallel\"]'"
    - id: TASK-SKILL-001
      title: sdd-build per-task commit + dispatch conduct
      requirements: [REQ-002, REQ-003]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-build/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs, commit: "docs(sdd): commit + parallel dispatch conduct" }
      acceptance: ["Step 4.9 commit conduct; dispatch preconditions; serialize-on-conflict"]
      verification:
        green: "grep -q 'Step 4.9' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-TMPL-001
      title: Report Commit column
      requirements: [REQ-004]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs2, commit: "docs(sdd): task commit column" }
      acceptance: ["Commit column with sha/unavailable/session vocabulary"]
      verification:
        green: "grep -q 'unavailable' .claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
    - id: TASK-SKILL-002
      title: sdd-autopilot composition note
      requirements: [REQ-005]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-autopilot/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs3, commit: "docs(sdd): task-commit composition under /auto" }
      acceptance: ["task commits + checkpoints coexist; budget respected"]
      verification:
        green: "grep -q 'per-task commits' .claude/skills/sdd-autopilot/SKILL.md"
    - id: TASK-TEST-001
      title: Documental anchors
      requirements: [REQ-007]
      depends_on: [TASK-CONTRACT-001, TASK-SKILL-001, TASK-TMPL-001, TASK-SKILL-002]
      files: { create: [tests/test_commit_parallel.py], modify: [], tests: [tests/test_commit_parallel.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): commit/parallel anchors" }
      acceptance: ["block shape, conduct anchors, column, autopilot note, history"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_commit_parallel.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-CONTRACT-001 | tests/test_commit_parallel.py | contract |
| 2 | REQ-002 | MUST | TASK-SKILL-001 | tests/test_commit_parallel.py | deterministic_inspection |
| 3 | REQ-003 | MUST | TASK-SKILL-001 | tests/test_commit_parallel.py | deterministic_inspection |
| 4 | REQ-004 | MUST | TASK-TMPL-001 | tests/test_commit_parallel.py | deterministic_inspection |
| 5 | REQ-005 | MUST | TASK-SKILL-002 | tests/test_commit_parallel.py | deterministic_inspection |
| 6 | REQ-006 | MUST | TASK-CONTRACT-001 | tests/test_commit_parallel.py | contract |
| 7 | REQ-007 | SHOULD | TASK-TEST-001 | tests/test_commit_parallel.py | deterministic_inspection |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `WORKFLOW_CONTRACTS.yaml` | Modify | `commit_parallel` block + v3.14.0 | (general) | None |
| 2 | `.claude/skills/sdd-build/SKILL.md` | Modify | Step 4.9 + dispatch policy | (general) | 1 |
| 3 | `BUILD_REPORT_TEMPLATE.md` | Modify | Commit column | (general) | 1 |
| 4 | `.claude/skills/sdd-autopilot/SKILL.md` | Modify | Composition note | (general) | 1 |
| 5 | `tests/test_commit_parallel.py` | Create | Documental anchors | @test-generator | 1–4 |

**Total Files:** 5

**`commit_parallel` block (file 1, exact shape):**

```yaml
commit_parallel:
  commit_rules:
    - "one commit per task, message from the manifest's execution.commit (Conventional Commits)"
    - "never mix independent tasks in one commit"
    - "never commit failing tests — except an explicitly marked RED commit"
    - "never rewrite history without explicit authorization"
    - "squash/rebase on merge is the maintainer's decision, not the build's"
  commit_recording:
    vocabulary: [sha, unavailable, session]
    unavailable: "no Git in the environment — recorded, never a blocker"
    session: "v1 builds or impractical granularity — justification in the task row's Notes"
  parallel_preconditions:
    - "all dependencies complete"
    - "write-sets disjoint (validated at Design: TM.write_conflict)"
    - "no shared migration or contract artifact in dispute"
    - "agent budget allows concurrent dispatch"
    - "merge strategy defined for the group"
  on_conflict: "serialize the remainder of the group — never an automatic risky merge"
```

---

## Agent Assignment Rationale

| Agent | Files | Citation (routing.json) |
|-------|-------|-------------------------|
| @test-generator | 5 | "Test automation expert for Python … pytest" |
| (general) | 1, 2, 3, 4 | Skill citation: `component-model` |

---

## Code Patterns

### Skill conduct shape (file 2 — Step 4.9)

```markdown
### Step 4.9: Commit the Task
After verification and the Step 4.6 review resolve, commit exactly this
task's files with its manifest `execution.commit` message; record the short
SHA in the Task Execution Commit column. No Git → `unavailable`. Never mix
tasks; never commit failing tests (a RED commit must be explicitly marked).
```

### Dispatch policy shape (file 2 — Step 2 v2 branch)

```markdown
Same-`parallel_group` tasks whose dependencies are complete MAY be dispatched
concurrently — their write-sets were validated disjoint at Design. All five
`commit_parallel.parallel_preconditions` must hold; any conflict or
precondition failure serializes the remainder (`on_conflict`).
```

---

## Data Flow

```text
1. Task verified + reviewed → committed with its declared message → SHA in report
2. Ready same-group tasks → preconditions check → concurrent dispatch or serialize
3. Branch review sees the integrated result; maintainer owns squash/rebase at merge
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Git (optional) | CLI | n/a — absence degrades to `unavailable` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Contract (documental) | Block shape (5+5+vocab), skill anchors, column, autopilot note, history | file 5 | pytest | AT-001…AT-007; ≥9 tests |
| Regression | No linter change; prior suites intact | existing suites | pytest | AT-008/009 |
| Parity | Post-repackage | existing | pytest | AT-010 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Git absent | `commit: unavailable` recorded; build proceeds | No |
| Commit fails (hooks, locks) | Record `unavailable` with the error in Notes; never a blocker | No |
| Runtime write collision in a parallel group | Serialize the remainder; record in Autonomous Decisions | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `commit_parallel.commit_rules` | list | 5 rules | §13.1 as data |
| `commit_parallel.commit_recording.vocabulary` | list | sha/unavailable/session | Report column tokens |
| `commit_parallel.parallel_preconditions` | list | 5 preconditions | §13.2 as data |
| `commit_parallel.on_conflict` | str | serialize | Never auto-merge |

---

## Security Considerations

- No history rewrites without authorization (rule as data); squash/rebase stays human-owned at merge time.
- Parallel dispatch bounded by validated write-sets + agent budget.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Linkage | Commit column ties each task to its SHA and verifications |
| Dispatch | Serialization events recorded in Autonomous Decisions |

---

## Pipeline Architecture (if applicable)

Not applicable.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial — 3 [ASSUMED] decisions (≥ 0.88), 5-task v2 manifest, matrix |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_COMMIT_PARALLEL_POLICY.md`
