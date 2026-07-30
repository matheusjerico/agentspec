# DESIGN: Linter Fail Closed

> Three fail-open paths become fail-closed: present-but-invalid config blocks exit 2 at the CLI (both phases), and malformed matrix/task-review rows become FAIL findings instead of silent drops — with the family arming unchanged, so unconfigured repos see zero new behavior.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LINTER_FAIL_CLOSED |
| **Date** | 2026-07-30 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_LINTER_FAIL_CLOSED.md](DEFINE_LINTER_FAIL_CLOSED.md) |
| **Status** | ✅ Complete (Built) |
| **Risk Level** | medium (echo from DEFINE) |

---

## Architecture Overview

```text
            contracts YAML block state         →  CLI outcome (per block)
            ───────────────────────────           ─────────────────────────
            absent (key not in data)              rules dormant (unchanged)
            present + valid mapping               rules armed (unchanged)
            present + null/str/list/int           _OperationalError → exit 2   ← NEW

            filled-section numbered row        →  parser outcome
            ───────────────────────────           ─────────────────────────
            full cardinality, no placeholder      parsed row (unchanged)
            <N cells or {placeholder}             FAIL finding naming the row  ← NEW
                                                  (was: silent drop)
```

Blast surface: `cli.py` (6 wiring paths), `build_report.py` (2 parsers → 2 rules), `design_phase.py` (1 parser → 1 rule). No new configuration vocabulary; the malformed-row rules ride their existing family arming.

---

## Components

| Component | Change |
|-----------|--------|
| `cli.py` | `_build_report_contract`: 4 blocks distinguish absent / valid-dict / present-invalid (exit 2); `traceability` validates `verification_types` before arming. `_design_phase_contract` + routing: `task_manifest`/`traceability` present-invalid → exit 2, never a silent plain-contract downgrade |
| `contracts/build_report.py` | `_parse_matrix_rows` and the Task Reviews parse collect malformed rows; new `BR.matrix_row_malformed` and `BR.task_review_row_malformed` FAIL rules; residual comments removed |
| `contracts/design_phase.py` | `_parse_matrix_rows` collects malformed rows; new `TX.matrix_row_malformed` FAIL rule; residual comment removed |
| `WORKFLOW_CONTRACTS.yaml` | v3.17.0 + history entry (no vocabulary change) |
| `tools/spec-linter/USAGE.md` | Fail-closed configuration note |
| `tests/` (both suites) | TDD RED-first rule/wiring tests + one root documental history pin |

---

## Key Decisions

### Decision 1: Malformed-row rules ride the family arming `[ASSUMED 0.90]`

`BR.matrix_row_malformed` arms with `matrix_must_coverage` (the `traceability` block), `BR.task_review_row_malformed` with `task_review_verdicts`, `TX.matrix_row_malformed` with `verification_types` — a repo that never configured the family sees no new findings. Rejected: always-on rules — they would lint matrix-shaped tables in repos that never adopted Increment 5/6, breaking the program's opt-in compatibility promise. Fail-closed applies where the control is ON; absence of the control stays a visible configuration choice.

### Decision 2: Present-but-null detected via `key in data` `[ASSUMED 0.92]`

`data.get(k)` conflates absent with explicit `k:` (yaml null). The check becomes: `if k in data and not isinstance(data[k], dict): raise _OperationalError`. Explicit null is a malformed block (someone wrote the key and lost the body — the indentation-drift scenario from the review), so it fails closed; a missing key remains the sanctioned dormant path.

### Decision 3: Routing gates on key presence; type validation raises inside the constructor `[ASSUMED 0.90]`

The design-phase router selects `DesignPhaseContract` when either key is **present** (any type) and the constructor then validates types — so `task_manifest: "yes"` reaches the validating path and exits 2 instead of silently falling to the plain section-only contract. Both-absent keeps today's plain-contract path byte-for-byte.

Gate D: all three ≥ 0.90 — no pauses. (Interactive run; threshold 0.80.)

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CLI-001
      title: Fail-closed wiring — 4 build blocks + 2 design blocks + routing
      requirements: [REQ-001, REQ-002]
      depends_on: []
      files: { create: [], modify: [tools/spec-linter/spec_linter/cli.py], tests: [tools/spec-linter/tests/test_cli.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: cli, commit: "fix(spec-linter): fail-closed config wiring" }
      acceptance: ["present-invalid (null/str/list/int) -> exit 2 naming block+type; absent -> dormant; traceability validates verification_types before arming; design routing never silently downgrades"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_cli.py -q  # new cases written first, fail"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-LINT-001
      title: BR.matrix_row_malformed + BR.task_review_row_malformed — TDD
      requirements: [REQ-003, REQ-005]
      depends_on: []
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: build-rules, commit: "fix(spec-linter): malformed matrix/review rows fail closed" }
      acceptance: ["<8-cell or placeholder REQ/Priority matrix row -> FAIL naming row, any risk; <5-cell or placeholder review row -> FAIL independent of the missing-rule severity gate; residual comments removed; intact fixtures unchanged"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_build_report_contract.py -q"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-LINT-002
      title: TX.matrix_row_malformed — TDD
      requirements: [REQ-004]
      depends_on: []
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/design_phase.py], tests: [tools/spec-linter/tests/test_design_phase_contract.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: design-rules, commit: "fix(spec-linter): design matrix rows fail closed" }
      acceptance: ["<6-cell or placeholder REQ/Priority design matrix row -> FAIL naming row; armed with verification_types; residual comment removed"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_design_phase_contract.py -q"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-DATA-001
      title: v3.17.0 + history entry
      requirements: [REQ-006]
      depends_on: [TASK-CLI-001, TASK-LINT-001, TASK-LINT-002]
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: data, commit: "chore(sdd): v3.17.0 fail-closed hardening history" }
      acceptance: ["version 3.17.0 in header+field; history entry names the 3 rules and the 6 wiring paths"]
      verification:
        green: "python3 -c 'import yaml; d=yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\")); assert d[\"version\"]==\"3.17.0\"'"
    - id: TASK-DOC-001
      title: USAGE.md fail-closed note
      requirements: [REQ-008]
      depends_on: [TASK-CLI-001]
      files: { create: [], modify: [tools/spec-linter/USAGE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs, commit: "docs(spec-linter): fail-closed config note" }
      acceptance: ["states: present-but-invalid blocks are exit-2 errors, never silent disables"]
      verification:
        green: "grep -qi 'fail-closed' tools/spec-linter/USAGE.md"
    - id: TASK-TEST-001
      title: Root documental history pin
      requirements: [REQ-006, REQ-007]
      depends_on: [TASK-DATA-001]
      files: { create: [], modify: [tests/test_workflow_metrics.py], tests: [tests/test_workflow_metrics.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): v3.17.0 history pin" }
      acceptance: ["history[0] is 3.17.0 naming the hardening; prior 3.16.0 pin updated to history[1]"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_workflow_metrics.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-CLI-001 | tools/spec-linter/tests/test_cli.py | unit |
| 2 | REQ-002 | MUST | TASK-CLI-001 | tools/spec-linter/tests/test_cli.py | unit |
| 3 | REQ-003 | MUST | TASK-LINT-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 4 | REQ-004 | MUST | TASK-LINT-002 | tools/spec-linter/tests/test_design_phase_contract.py | unit |
| 5 | REQ-005 | MUST | TASK-LINT-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 6 | REQ-006 | MUST | TASK-DATA-001, TASK-TEST-001 | tests/test_workflow_metrics.py | contract |
| 7 | REQ-007 | SHOULD | TASK-CLI-001, TASK-LINT-001, TASK-LINT-002 | all three linter test files | unit |
| 8 | REQ-008 | COULD | TASK-DOC-001 | grep verification | deterministic_inspection |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `tools/spec-linter/tests/test_cli.py` | Modify | RED-first wiring cases | (general) | None |
| 2 | `tools/spec-linter/spec_linter/cli.py` | Modify | Fail-closed wiring (6 paths + routing) | (general) | 1 |
| 3 | `tools/spec-linter/tests/test_build_report_contract.py` | Modify | RED-first malformed-row cases | (general) | None |
| 4 | `tools/spec-linter/spec_linter/contracts/build_report.py` | Modify | 2 new FAIL rules | (general) | 3 |
| 5 | `tools/spec-linter/tests/test_design_phase_contract.py` | Modify | RED-first design cases | (general) | None |
| 6 | `tools/spec-linter/spec_linter/contracts/design_phase.py` | Modify | 1 new FAIL rule | (general) | 5 |
| 7 | `WORKFLOW_CONTRACTS.yaml` | Modify | v3.17.0 + history | (general) | 2, 4, 6 |
| 8 | `tools/spec-linter/USAGE.md` | Modify | Fail-closed note | (general) | 2 |
| 9 | `tests/test_workflow_metrics.py` | Modify | History pin update | @test-generator | 7 |

---

## Agent Assignment Rationale

| Agent | Files | Why |
|-------|-------|-----|
| (general) | 1–8 | Parser/CLI hardening following the established rule patterns — no specialist gap (autoprovision sensor: 0 citations) |
| @test-generator | 9 | Documental pin, same as prior increments |

---

## Code Patterns

### Fail-closed wiring (per block, cli.py)

```python
for key in ("tdd_policy", "task_review", "traceability", "workflow_metrics"):
    if key in data and not isinstance(data[key], dict):
        raise _OperationalError(
            f"{key} must be a mapping in {contracts_file.name} — "
            f"got {type(data[key]).__name__}; a present-but-invalid block "
            f"fails closed instead of silently disarming its rules"
        )
```

### Malformed-row collection (parsers)

```python
malformed: list[str] = []
for m in _NUMBERED_ROW.finditer(section):
    cells = [c.strip() for c in m.group(0).strip("|").split("|")]
    if len(cells) < 8 or "{" in cells[1] or "{" in cells[2]:
        malformed.append(m.group(0).strip())   # was: continue (silent)
        continue
    rows.append(...)
```

Each malformed entry becomes one FAIL finding (`field` = the section, `found` = the offending row text) in the family's check method — severity independent of any risk-level gate.

### Schema Evolution Plan

No schema change — v3.17.0 records behavior hardening only; the YAML vocabulary and all block shapes are unchanged. Rollback = revert the PR (prior tolerance restored).

---

## Data Flow

1. CLI loads contracts → per-block: absent = dormant, valid dict = armed, present-invalid = exit 2 →
2. Parsers collect malformed numbered rows instead of dropping them →
3. Family check methods emit the new FAIL rules alongside the existing ones →
4. Gate L consumes verdicts that can no longer be hollowed out by truncation or config drift.

---

## Integration Points

| Point | Contract |
|-------|----------|
| Family arming | Unchanged — the new rules activate exactly with their family (`traceability`, `task_review`, `verification_types`) |
| Legacy reports | Unchanged — no Schema Version row still routes to `_check_legacy`, which the new rules never join |
| Plugin | `plugin/tools/spec-linter` regenerated by `./build-plugin.sh`; parity via `tests/test_plugin_parity.py` |
| Autopilot Gate L | Exit 2 (config error) remains sensor-unavailable → VISIBLE SKIP; the hardening turns silent disarms into that visible state |

---

## Testing Strategy

| Layer | Tests |
|-------|-------|
| Unit — wiring (TDD RED-first) | 4 build blocks + 2 design blocks × {null, string, list} → exit-2 `_OperationalError`; absent → dormant green; `traceability` dict without `verification_types` → error (build side now, design side already) |
| Unit — rules (TDD RED-first) | build matrix rows of 1–7 cells; placeholder REQ; placeholder Priority; review rows <5 cells containing `dirty`; placeholder verdict — at risk low; design matrix rows 1–5 cells + placeholders; intact fixtures produce zero new findings |
| Contract | v3.17.0 history pin (root suite) |
| Regression | Full suites (root ≥172, linter ≥193) + plugin parity |

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Present-invalid block | `_OperationalError` → exit 2 naming block + found type — autopilot treats as VISIBLE SKIP, never assumed PASS |
| Malformed row | FAIL finding naming the row text — report blocked until the row is fixed or removed |
| Unconfigured family | No change — rules dormant, exactly today's posture |

---

## Configuration

None added. The change is tolerance-tightening on the existing configuration surface.

---

## Security Considerations

Hardening only — closes the "typo disables the control" and "truncation hides the finding" surfaces the review demonstrated.

---

## Observability

New findings carry the offending row text in `found`; exit-2 messages name the block and the found Python type — both directly actionable.

---

## Pipeline Architecture (if applicable)

Not applicable — framework tooling.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-30 | design-agent | Initial — Codex review findings 1–3 under autopilot conduct |

---

## Next Step

`/build .claude/sdd/features/DESIGN_LINTER_FAIL_CLOSED.md` (autopilot continues)
