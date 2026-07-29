# DESIGN: Workflow Metrics

> A `workflow_metrics` v1 schema inside the BUILD_REPORT — emitted by Build from measured values only, validated by the linter (null needs a reason, estimates are findings), summarized by Ship, and forbidden from changing any policy on its own.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | WORKFLOW_METRICS |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_WORKFLOW_METRICS.md](DEFINE_WORKFLOW_METRICS.md) |
| **Status** | Ready for Build |
| **Risk Level** | medium (echo from DEFINE) |

---

## Architecture Overview

```text
                     WORKFLOW_CONTRACTS.yaml v3.16.0
                     └─ workflow_metrics: schema_version 1, key catalog,
                        availability rule, behavior per consumer
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  sdd-build SKILL            spec-linter                 sdd-ship SKILL
  EMITS the block            VALIDATES (BR.metrics_*)    SUMMARIZES into SHIPPED
  measured-only;             present/parseable/version/  + no-adaptive-automation
  null + reason              null-reason/no-estimates    boundary (§15.3)
        │                          ▲                          ▲
        └──────► BUILD_REPORT ─────┴──────────────────────────┘
                 ## Workflow Metrics
                 ```yaml
                 workflow_metrics:
                   schema_version: 1
                   ...
                 ```
```

One artifact (the report), three consumers, zero new files at runtime. Comparing two runs = diffing two same-version YAML blocks — no prose parsing (§15.4).

---

## Components

| Component | Change |
|-----------|--------|
| `WORKFLOW_CONTRACTS.yaml` | New `workflow_metrics` block (schema_version 1, 13-key catalog, availability rule, behavior) + `metrics` wiring under `build.report_contract`; v3.16.0 + history |
| `BUILD_REPORT_TEMPLATE.md` | New **Workflow Metrics** section with the fenced yaml block skeleton |
| `tools/spec-linter/.../build_report.py` | Metrics extraction (exact-slug section scoping) + 5 BR.metrics rules; None-default constructor params |
| `tools/spec-linter/.../cli.py` | Wire `metrics` config from the build contract block into `BuildReportContract` |
| `sdd-build SKILL` | Emission conduct: measured-only, null+reason, estimation forbidden |
| `sdd-ship SKILL` | Metrics summary into SHIPPED + the §15.3 boundary |
| `tests/` + `tools/spec-linter/tests/` | Documental anchors + TDD-first unit tests |

---

## Key Decisions

### Decision 1: The block lives inside BUILD_REPORT, not an adjacent file `[ASSUMED 0.92]`

§15.2 allows either. Inside the report wins: single-artifact story (the task manifest precedent — Inc 3 parses fenced yaml from DESIGN), the ship gate already reads the report, archives stay self-contained, and no new file lifecycle to define. Rejected: `WORKFLOW_METRICS_{FEATURE}.yaml` sidecar — one more file to archive, clean, and parity-check for zero added capability.

### Decision 2: Unavailable = `{value: null, reason: "..."}` mapping; measured = plain scalar `[ASSUMED 0.90]`

The availability rule needs a machine-checkable shape. A key that was measured holds a plain scalar/map (`build: 2551`); a key the run could not measure holds exactly `{value: null, reason: "<why>"}`. A bare `key: null` (no reason) is a linter FAIL, and estimate markers (`~`, `approx`, `estimated`) in values are FAILs — measured or null, never in between. Rejected: sidecar `*_reason` keys (pollutes the catalog; easy to orphan).

### Decision 3: Closed key catalog in the contract; presence required, value nullable `[ASSUMED 0.90]`

The contract lists the 13 catalog keys (§15.1). All must be PRESENT in an emitted block (comparability needs a stable shape — §15.4); any may be the null+reason mapping (honesty needs an escape hatch). `tokens_cost` is expected to be null+reason in most environments — exactly per §15.1's "somente quando a plataforma os fornecer de modo confiável". Closed-vocabulary validation follows the program's recurring lesson (unknown top-level keys under `workflow_metrics:` → FAIL, catching typos like `phase_durations`).

Gate D: all three ≥ 0.90 — no pauses. (Interactive run; threshold 0.80.)

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: workflow_metrics block + build.report_contract.metrics wiring + v3.16.0
      requirements: [REQ-001, REQ-006, REQ-008]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: contract, commit: "feat(sdd): workflow_metrics contract data" }
      acceptance: ["yaml.safe_load exposes workflow_metrics: schema_version 1, 13 catalog keys, availability rule, behavior; comparability comment (REQ-008)"]
      verification:
        green: "python3 -c 'import yaml; b=yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"workflow_metrics\"]; assert b[\"schema_version\"]==1'"
    - id: TASK-TMPL-001
      title: BUILD_REPORT_TEMPLATE Workflow Metrics section
      requirements: [REQ-002]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tmpl, commit: "docs(sdd): metrics section in report template" }
      acceptance: ["section holds fenced yaml workflow_metrics skeleton with all 13 keys"]
      verification:
        green: "grep -q 'workflow_metrics:' .claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
    - id: TASK-LINT-001
      title: BR.metrics rules (present/parseable/version/null-reason/no-estimates) — TDD
      requirements: [REQ-005, REQ-007]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py, tools/spec-linter/spec_linter/cli.py], tests: [tools/spec-linter/tests/test_metrics_rules.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: lint, commit: "feat(spec-linter): BR.metrics rules" }
      acceptance: ["valid passes; null-no-reason/version-mismatch/estimate-marker/unknown-key FAIL; absent block follows legacy mode; None-default params keep old constructors green"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_metrics_rules.py -q  # written first, fails before implementation"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-SKILL-001
      title: sdd-build emission conduct
      requirements: [REQ-003]
      depends_on: [TASK-CONTRACT-001, TASK-TMPL-001]
      files: { create: [], modify: [.claude/skills/sdd-build/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: docs, commit: "docs(sdd): build emits measured metrics" }
      acceptance: ["measured-only; null+reason; estimating/interpolating/copying prior runs forbidden"]
      verification:
        green: "grep -q 'workflow_metrics' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-SKILL-002
      title: sdd-ship summary + no-adaptive-automation boundary
      requirements: [REQ-004]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-ship/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs2, commit: "docs(sdd): ship summarizes metrics" }
      acceptance: ["summary into SHIPPED; metrics never auto-change policies; recalibration needs comparable runs + human review"]
      verification:
        green: "grep -q 'workflow_metrics' .claude/skills/sdd-ship/SKILL.md"
    - id: TASK-TEST-001
      title: Documental anchors (root suite)
      requirements: [REQ-007]
      depends_on: [TASK-CONTRACT-001, TASK-TMPL-001, TASK-LINT-001, TASK-SKILL-001, TASK-SKILL-002]
      files: { create: [tests/test_workflow_metrics.py], modify: [], tests: [tests/test_workflow_metrics.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): workflow metrics anchors" }
      acceptance: ["contract block shape + availability rule; template section; build/ship conduct incl. the boundary; comparability (AT-009) via two-block key diff"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_workflow_metrics.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | contract |
| 2 | REQ-002 | MUST | TASK-TMPL-001 | tests/test_workflow_metrics.py | deterministic_inspection |
| 3 | REQ-003 | MUST | TASK-SKILL-001 | tests/test_workflow_metrics.py | deterministic_inspection |
| 4 | REQ-004 | MUST | TASK-SKILL-002 | tests/test_workflow_metrics.py | deterministic_inspection |
| 5 | REQ-005 | MUST | TASK-LINT-001 | tools/spec-linter/tests/test_metrics_rules.py | unit |
| 6 | REQ-006 | MUST | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | contract |
| 7 | REQ-007 | SHOULD | TASK-LINT-001, TASK-TEST-001 | tools/spec-linter/tests/test_metrics_rules.py, tests/test_workflow_metrics.py | unit |
| 8 | REQ-008 | COULD | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | deterministic_inspection |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `WORKFLOW_CONTRACTS.yaml` | Modify | `workflow_metrics` block + wiring + v3.16.0 | (general) | None |
| 2 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Workflow Metrics section | (general) | 1 |
| 3 | `tools/spec-linter/tests/test_metrics_rules.py` | Create | RED-first unit tests | (general) | 1 |
| 4 | `tools/spec-linter/spec_linter/contracts/build_report.py` | Modify | Extraction + 5 rules | (general) | 3 |
| 5 | `tools/spec-linter/spec_linter/cli.py` | Modify | Config wiring | (general) | 4 |
| 6 | `.claude/skills/sdd-build/SKILL.md` | Modify | Emission conduct | (general) | 1, 2 |
| 7 | `.claude/skills/sdd-ship/SKILL.md` | Modify | Summary + boundary | (general) | 1 |
| 8 | `tests/test_workflow_metrics.py` | Create | Documental anchors | @test-generator | 1–7 |

---

## Agent Assignment Rationale

| Agent | Files | Why |
|-------|-------|-----|
| (general) | 1–7 | Contract data, template, linter rules following the established BR.* pattern — no specialist gap (specialist-autoprovision sensor: 0 citations) |
| @test-generator | 8 | Documental anchor suite, same as Increments 1–8 |

---

## Code Patterns

### Metrics block shape (template skeleton — file 2)

```yaml
workflow_metrics:
  schema_version: 1
  feature: "{FEATURE}"
  phase_duration_seconds: { build: 0 }           # measured, or {value: null, reason: "..."}
  time_to_first_green_seconds: { value: null, reason: "not instrumented" }
  task_count: 0
  effective_parallelism: 1
  tests_by_type: { unit: 0, contract: 0, documental: 0, integration: 0 }
  reopened_tasks: 0
  fix_rounds: { local: 0, final: 0 }
  findings: { critical: 0, important: 0, minor: 0, by_stage: { task_review: 0, branch_review: 0 } }
  requirements: { must_total: 0, must_verified: 0, excepted: 0 }
  operational_skips: []                          # e.g. ["J:exit3"]
  risk_overrides: 0
  tokens_cost: { value: null, reason: "platform does not expose reliable per-run tokens" }
```

### Rule scoping (file 4 — the recurring lesson applied)

```python
section = self._section_exact(report_text, "Workflow Metrics")   # exact slug, no prefix decoys
block = self._fenced_yaml(section, root_key="workflow_metrics")  # same extraction family as the task manifest
```

### Schema Evolution Plan

`schema_version` bumps on ANY key addition, removal, or shape change; the linter validates against the contract's version only — a mismatched block is a FAIL, never a coerced parse. Consumers compare only same-version blocks. v1→v2 migration guidance would ride the contract's version_history (no silent widening).

---

## Data Flow

1. Build finishes → sdd-build fills the template's block with **measured** values (or null+reason) →
2. `spec-lint --phase build` runs BR.metrics_* alongside the existing BR.* rules →
3. Ship's Gate S consumes the validated report; SHIPPED gets a metrics summary table →
4. Two archived reports diff key-by-key (same schema_version) — rigor/cost/defect deltas without prose.

---

## Integration Points

| Point | Contract |
|-------|----------|
| `build.report_contract.metrics` | `{ configured: true, schema_version: 1 }` — opt-in like `manifest_configured`; absent → rules dormant |
| Legacy mode | Absent block on a configured repo: WARN in `--legacy-mode warn`, FAIL in `fail`; pre-Inc-9 archives are never linted retroactively |
| Run ledger | Unchanged — metrics complement it; `operational_skips` mirrors SKIP rows (e.g. `J:exit3`) |
| Plugin | Step 5e parity covers contracts YAML + template + skills; linter code is repo-only (not shipped) as in Inc 1–6 |

---

## Testing Strategy

| Layer | Tests |
|-------|-------|
| Unit (§16.1, TDD RED-first) | valid block exit 0 · bare null FAIL · version mismatch FAIL · estimate marker FAIL · unknown key FAIL · missing catalog key FAIL · absent block warn/fail by legacy mode · not-configured → dormant |
| Contract (§16.2) | contract block shape; template↔contract key parity (13/13); version history entry |
| Documental | build conduct (measured-only, forbidden verbs); ship summary + §15.3 boundary verbatim; comparability example |
| Dogfood (§16.4) | This run's own BUILD_REPORT emits the first real block — honest nulls where the run didn't measure |

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Unparseable yaml in the block | FAIL BR.metrics_parseable naming the parse error — never a silent skip |
| Null without reason / estimate marker | FAIL naming the exact key |
| Report without the section (configured) | Legacy-mode path (warn/fail) — compatibility for mid-migration repos |
| Linter crash on metrics code | Exit ≥ 2 → autopilot Gate L treats as sensor-unavailable: VISIBLE SKIP, never assumed PASS |

---

## Configuration

All in `WORKFLOW_CONTRACTS.yaml`: the `workflow_metrics` catalog (single source), plus the two-field wiring under `build.report_contract.metrics`. No env vars, no CLI flags beyond the existing `--phase build --legacy-mode`.

---

## Security Considerations

None material — local artifact, no external transmission (telemetry upload explicitly out of scope). `tokens_cost` stays null unless the platform provides it; no scraping of billing surfaces.

---

## Observability

The feature IS the observability layer: the block is the machine-readable surface, the SHIPPED summary the human one, and the ledger remains the run's event log.

---

## Pipeline Architecture (if applicable)

Not applicable — framework feature.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent | Initial — plan §15/§16 under autopilot conduct |

---

## Next Step

`/build .claude/sdd/features/DESIGN_WORKFLOW_METRICS.md` (autopilot continues)
