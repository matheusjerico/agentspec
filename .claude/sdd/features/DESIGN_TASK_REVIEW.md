# DESIGN: Task Review

> Technical design for incremental per-task review: `task_review` contract block, two BuildReportContract rules keyed on the report's Risk Level, a Task Reviews report section, and the blind-first review step in sdd-build's execution loop.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TASK_REVIEW |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_TASK_REVIEW.md](./DEFINE_TASK_REVIEW.md) |
| **Risk Level** | medium (echo from DEFINE — build-loop conduct + report contract) |
| **Status** | Ready for Build |
| **Design Confidence** | 0.90 — fifth extension of the established contract pattern |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│              INCREMENTAL TASK REVIEW — SYSTEM DIAGRAM                 │
├──────────────────────────────────────────────────────────────────────┤
│  sdd-build execution loop (per task, after verification):            │
│    dispatch manifest `reviewer` BLIND-FIRST (§11.3): requirements,   │
│    acceptance, task diff, tests, dependent interfaces, risks —       │
│    NEVER the implementer's rationale before the initial assessment   │
│    → verdict: clean / clean-with-minors / dirty / skipped-by-policy  │
│    → blocking findings: 1 fix round (separate from final review's 2) │
│    → still dirty: dependents DO NOT start; verdict recorded           │
│                                                                      │
│  BUILD_REPORT ## Task Reviews                                        │
│    | # | Task ID | Risk | Reviewer | Verdict | Blocking/Minor | Rounds│
│                                                                      │
│  spec-lint --phase build (BuildReportContract, extended):            │
│    BR.task_review_missing  (v2 + Risk Level row present)             │
│      report high|critical: no section, or a manifest task row        │
│      without a matching review row → FAIL                            │
│      medium → WARN · low / no Risk Level row → silent                │
│    BR.task_review_dirty                                              │
│      any review verdict `dirty` → FAIL · invalid token → FAIL        │
│                                                                      │
│  Branch-level final review (Step 5.5 / Gate R): UNCHANGED, mandatory │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `task_review` contract block | Verdict vocabulary, per-risk policy, per-task fix budget (1, separate from final 2), blind-first rule, enforcement map (v3.12.0) | YAML |
| `BuildReportContract` extension | 2 rules parameterized from the block; optional params (None → off) | Python, existing contract |
| `## Task Reviews` report section | Numbered rows: Task ID, risk, reviewer, verdict, blocking/minor counts, fix rounds | Markdown template |
| sdd-build review step | Step 4.6 in the execution loop: dispatch, blind-first, budget, verdict, dependents gate | Skill markdown |

---

## Key Decisions

### Decision 1: Enforcement keys on the REPORT's Risk Level; task-level risk refines conduct `[ASSUMED 0.90]`
The linter fires on the report-level risk (same opt-in markers as Increment 4: schema v2 + Risk Level row). Per-task `risk` from the manifest decides WHO reviews (policy conduct in sdd-build); WHETHER rules fire is report-level (deterministic, already parsed). Per-task enforcement can land later, additively (DEFINE A-003).

### Decision 2: Review rows matched to task rows by Task ID equality `[ASSUMED 0.90]`
Task Execution rows carry Task IDs since Increment 3 (`-` for v1). Rule: every Task Execution row whose Task ID ≠ `-` must have a Task Reviews row with the same ID (high/critical FAIL; medium WARN). v1 builds are structurally exempt. Reuses `_NUMBERED_ROW` cell parsing (verdict = 5th cell).

### Decision 3: `skipped-by-policy` is a valid verdict everywhere `[ASSUMED 0.85]`
The linter cannot judge task relevance (a docs task at high risk is legitimately skippable). A skipped-by-policy ROW is a recorded decision — reviewable conduct; a MISSING row is the violation. Deterministic and honest; the review row's policy citation (COULD) makes it auditable.

### Decision 4: Blind-first is conduct + documental anchor, not a sensor `[ASSUMED 0.90]`
Same boundary as Increment 4's RED validity: no deterministic sensor can verify what a reviewer saw. The rule lives as contract data + skill obligation + anchor test.

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: task_review block + v3.12.0 history
      requirements: [MUST-1, MUST-6]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: contract, commit: "feat(sdd): task_review contract data" }
      acceptance: ["yaml.safe_load exposes task_review vocabularies"]
      verification:
        green: "python3 -c 'import yaml; yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"task_review\"]'"
    - id: TASK-LINTER-001
      title: BR.task_review_missing + BR.task_review_dirty
      requirements: [MUST-4]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py], tests: [] }
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: linter, commit: "feat(spec-linter): task-review rules" }
      acceptance: ["high/critical missing FAIL; medium WARN; dirty FAIL; invalid token FAIL; low/legacy silent"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-LINTER-002
      title: CLI task_review wiring (tolerant when absent)
      requirements: [MUST-4]
      depends_on: [TASK-LINTER-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/cli.py], tests: [] }
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: linter, commit: "feat(spec-linter): wire task_review" }
      acceptance: ["block present → armed; absent → off; malformed → exit 2"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-TEST-001
      title: Rule tests
      requirements: [SC-1, SC-2]
      depends_on: [TASK-LINTER-001]
      files: { create: [], modify: [tools/spec-linter/tests/test_build_report_contract.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): task-review coverage" }
      acceptance: ["≥8 tests across both families + silences"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_build_report_contract.py -q"
    - id: TASK-TEST-002
      title: CLI tests
      requirements: [SC-2]
      depends_on: [TASK-LINTER-002]
      files: { create: [], modify: [tools/spec-linter/tests/test_cli.py], tests: [tools/spec-linter/tests/test_cli.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): task_review CLI coverage" }
      acceptance: ["armed exit 1; absent block exit 0; malformed exit 2"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_cli.py -q"
    - id: TASK-SKILL-001
      title: sdd-build per-task review step (blind-first, budget, dependents gate)
      requirements: [MUST-2, MUST-5]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-build/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: docs, commit: "docs(sdd): per-task review conduct" }
      acceptance: ["flow step present; final review untouched"]
      verification:
        green: "grep -q 'blind-first' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-TMPL-001
      title: BUILD_REPORT Task Reviews section
      requirements: [MUST-3]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs2, commit: "docs(sdd): Task Reviews section" }
      acceptance: ["section + column shape documented"]
      verification:
        green: "grep -q '## Task Reviews' .claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
    - id: TASK-TEST-003
      title: Documental anchors
      requirements: [SC-3, SC-4]
      depends_on: [TASK-CONTRACT-001, TASK-SKILL-001, TASK-TMPL-001]
      files: { create: [tests/test_task_review.py], modify: [], tests: [tests/test_task_review.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): task-review anchors" }
      acceptance: ["block shape, skill anchors, template markers, final-review invariance, history"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_task_review.py -q"
    - id: TASK-DOCS-001
      title: USAGE.md task-review rules
      requirements: [MUST-4]
      depends_on: [TASK-LINTER-002]
      files: { create: [], modify: [tools/spec-linter/USAGE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs3, commit: "docs(spec-linter): task-review rules" }
      acceptance: ["both rules + silences documented"]
      verification:
        green: "grep -q 'task_review_missing' tools/spec-linter/USAGE.md"
```

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `WORKFLOW_CONTRACTS.yaml` | Modify | `task_review` block + v3.12.0 + history | (general) | None |
| 2 | `build_report.py` | Modify | 2 rules + Task Reviews section parsing | @python-developer | 1 |
| 3 | `cli.py` | Modify | task_review wiring, tolerant fallback | @python-developer | 2 |
| 4 | `test_build_report_contract.py` | Modify | ≥8 rule tests | @test-generator | 2 |
| 5 | `test_cli.py` | Modify | ≥3 CLI tests | @test-generator | 3 |
| 6 | `.claude/skills/sdd-build/SKILL.md` | Modify | Step 4.6 per-task review | (general) | 1 |
| 7 | `BUILD_REPORT_TEMPLATE.md` | Modify | Task Reviews section | (general) | 1 |
| 8 | `tests/test_task_review.py` | Create | Documental anchors | @test-generator | 1, 6, 7 |
| 9 | `tools/spec-linter/USAGE.md` | Modify | Rules docs | (general) | 3 |

**Total Files:** 9

**`task_review` block (file 1, exact shape):**

```yaml
task_review:
  verdicts: [clean, clean-with-minors, dirty, skipped-by-policy]
  policy_by_risk:
    low: executor_checklist
    medium: selective_independent   # Warn rollout (§18 PR 5)
    high: independent_required
    critical: independent_plus_specialist
  blind_first: "the reviewer forms the initial assessment WITHOUT the implementer's rationale — context is requirements, acceptance, task diff, tests, dependent interfaces, risks"
  fix_budget_per_task: 1            # separate from build.execution.final_review.fix_loop_budget
  dependents_blocked_on: [dirty]
  enforcement:
    high_critical_missing: FAIL     # BR.task_review_missing
    medium_missing: WARN
    low_missing: silent
    no_risk_row: silent             # pre-Increment-2 adoption path
    dirty_verdict: FAIL             # BR.task_review_dirty — any risk
  invariant: "the whole-branch final review (build.execution.final_review) stays mandatory — task reviews never replace it"
```

**`## Task Reviews` section shape (file 7):**

```markdown
| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |
|---|---------|------|----------|---------|----------------------|------------|
| 1 | TASK-X-001 | medium | @code-reviewer | clean | 0 / 1 | 0/1 |
```

---

## Agent Assignment Rationale

| Agent | Files | Citation (routing.json) |
|-------|-------|-------------------------|
| @python-developer | 2, 3 | "Python code architect …", kb [python, pydantic, testing] |
| @test-generator | 4, 5, 8 | "Test automation expert for Python … pytest" |
| (general) | 1, 6, 7, 9 | Skill citation: `component-model` |

---

## Code Patterns

### Pattern 1: Review-row parsing (reuses existing cell machinery)

```python
# parse(): task_review_rows: list[tuple[str, str]]  # (task_id, verdict)
# from _NUMBERED_ROW matches inside _section_after(artifact, "task_reviews"):
#   cells[1] = Task ID, cells[4] = verdict (lowercased)
# task_ids_executed: set[str] — cells[1] of Task Execution rows, minus "-"
```

### Pattern 2: Missing/dirty checks

```python
def _check_task_reviews(self, parsed) -> list[Finding]:
    if not self._task_review_policy:      # block absent → off
        return []
    level = _risk_token(parsed)           # same extraction as Increment 4
    if level is None:
        return []                          # adoption path
    severity = {"high": FAIL, "critical": FAIL, "medium": WARN}.get(level)
    reviewed = {tid for tid, _ in parsed.task_review_rows}
    for tid in sorted(parsed.task_ids_executed - reviewed):
        if severity: findings.append(...)  # BR.task_review_missing per task
    for tid, verdict in parsed.task_review_rows:
        if verdict not in self._task_review_verdicts: FAIL ...
        elif verdict == "dirty": FAIL ...  # BR.task_review_dirty — any risk
```

---

## Data Flow

```text
1. Build executes a manifest task → verification passes
2. Step 4.6: dispatch the task's `reviewer` blind-first → verdict
   blocking findings → 1 fix round → still dirty: dependents blocked
3. Report: Task Reviews row per task (verdict, counts, rounds)
4. Gate: missing rows (high/critical FAIL, medium WARN), dirty FAIL
5. Step 5.5 branch review: UNCHANGED — integration lens on top
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| None | — | — |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit (rules) | missing (high FAIL / medium WARN / low silent / legacy silent / unreviewed-task), dirty FAIL, invalid token FAIL, all-clean pass | file 4 | pytest mutator | AT-001…AT-008; ≥8 tests |
| Integration (CLI) | armed / absent / malformed | file 5 | cli.main | ≥3 tests |
| Contract (documental) | block shape, blind-first + budget anchors, template, final-review invariance, history | file 8 | pytest | AT-009 |
| Parity | post-repackage | existing | pytest | AT-010 |
| E2E (dogfood) | This run's own report carries voluntary Task Reviews rows (medium — exercises shape without force) | gate runs | - | live |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `task_review` block absent | Rules off — backward compatible | No |
| Block present, malformed subkeys | `_OperationalError` exit 2 | No |
| Review row with unknown Task ID (no matching task) | No finding — extra rows are harmless records | No |
| v1 build (Task IDs `-`) | Structurally exempt from matching | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `task_review.verdicts` | list | 4 tokens | Vocabulary |
| `task_review.policy_by_risk` | map | §11.4 | Conduct policy (who reviews) |
| `task_review.fix_budget_per_task` | int | 1 | Separate from final review's 2 |
| `task_review.enforcement` | map | FAIL/WARN/silent split | Wired via CLI |

---

## Security Considerations

- No new blocking outside opt-in high/critical reports; final-review guarantees untouched.
- Linter validates recorded rows only — never dispatches reviews.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Findings | Rules name the task id and verdict verbatim |
| Metrics seed | Blocking/minor counts per task recorded — Increment 9's raw material |

---

## Pipeline Architecture (if applicable)

Not applicable.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial — 4 [ASSUMED] decisions (≥ 0.85), 9-task v2 manifest |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_TASK_REVIEW.md`
