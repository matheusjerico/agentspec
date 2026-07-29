# DESIGN: Risk Driven TDD

> Technical design for TDD-by-policy: a `tdd_policy` contract block, two BuildReportContract rules (risk-derived TDD floor, exception-category validation), skill/command conduct for effective-mode derivation and `--no-tdd`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_DRIVEN_TDD |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_RISK_DRIVEN_TDD.md](./DEFINE_RISK_DRIVEN_TDD.md) |
| **Risk Level** | medium (echo from DEFINE — blast_radius medium: report contract consumed by Build/Ship/Autopilot) |
| **Status** | ✅ Shipped |
| **Design Confidence** | 0.90 — fourth extension of a thrice-reviewed pattern |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│              RISK-DRIVEN TDD — SYSTEM DIAGRAM                         │
├──────────────────────────────────────────────────────────────────────┤
│  effective TDD = strongest of:                                       │
│    --tdd flag (opt-in) · risk_policy[Risk Level] · task tdd:required │
│  (derived by sdd-build, recorded as the report's TDD Mode row)       │
│                                                                      │
│  --no-tdd: dispenses low/medium ONLY, justification recorded;        │
│            refused + recorded at high/critical                       │
│                                                                      │
│  spec-lint --phase build (BuildReportContract, extended):            │
│    BR.tdd_required_by_risk                                           │
│      Risk Level high|critical + TDD Mode off  → FAIL (fail-closed)   │
│      Risk Level medium        + TDD Mode off  → WARN                 │
│      low / no Risk Level row (pre-Inc2)       → silent (adoption)    │
│    BR.tdd_exception_invalid                                          │
│      TDD Evidence rows may declare `exception: <category> — <alt>`   │
│      unknown/empty category → FAIL; categories are contract data     │
│                                                                      │
│  RED validity (§10.2, skill conduct): broken RED command, unrelated  │
│  import error, or pre-existing failure is NOT evidence               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `tdd_policy` contract block | Effective-mode rule, risk_policy map, --no-tdd constraints, exception categories, RED-validity statement — all as data (v3.11.0) | YAML |
| `BuildReportContract` extension | 2 new rules parameterized from the block; silent when the block or the Risk Level row is absent (backward compatible) | Python, existing contract |
| Skill/command conduct | sdd-build effective-mode derivation + `--no-tdd` semantics + §10.2 cycle; `/build` flag surface | Markdown |
| Template grammar | TDD Evidence exception-row format + new-test/regression/alternative distinction | Markdown |

---

## Key Decisions

### Decision 1: Extend `BuildReportContract` — no new contract class `[ASSUMED 0.90]`
The build phase already owns a semantic contract; two rules and two constructor params (`risk_tdd_policy: dict`, `tdd_exception_categories: list`) fit the established shape. CLI passes them from `tdd_policy` when present; absent block → both rules off (older contracts files unchanged).

### Decision 2: Risk Level token = first whitespace-delimited word, lowercased `[ASSUMED 0.85]`
`medium (echo from DEFINE — …)` → `medium`. Unknown token → both rules silent (validating the row's vocabulary is the define phase's RP surface, not the build gate's job; fail-open here is Observe/Warn-consistent because the FAIL floor only ever *adds* on recognized high/critical).

### Decision 3: Severity split exactly as the DEFINE fixes it `[ASSUMED 0.90]`
high/critical+off FAIL (both markers are opt-in artifacts — A-003), medium+off WARN, low/absent silent. `opt-in` and `required` both count as TDD active (Increment 1's evidence rule already covers section presence for both).

### Decision 4: Exception grammar is a scan, not a table parse `[ASSUMED 0.85]`
The linter scans the TDD Evidence section for every `exception: <token>` occurrence and validates each token against the categories list. Grammar in the template: `n/a — exception: <category>; verified by: <command>`. Whether a specific row *deserves* an exception is skill conduct (§10.3 approved_by_policy = category membership, A-004).

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: tdd_policy block + v3.11.0 history
      requirements: [MUST-1, MUST-6]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: contract, commit: "feat(sdd): tdd_policy contract data" }
      acceptance: ["yaml.safe_load exposes tdd_policy vocabularies"]
      verification:
        green: "python3 -c 'import yaml; yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"tdd_policy\"]'"
    - id: TASK-LINTER-001
      title: BuildReportContract TDD rules
      requirements: [MUST-5]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py], tests: [] }
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: linter, commit: "feat(spec-linter): risk-driven TDD rules" }
      acceptance: ["high/critical+off FAIL; medium+off WARN; low/legacy silent; unknown exception category FAIL"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-LINTER-002
      title: CLI tdd_policy params (tolerant when absent)
      requirements: [MUST-5]
      depends_on: [TASK-LINTER-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/cli.py], tests: [] }
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: linter, commit: "feat(spec-linter): wire tdd_policy" }
      acceptance: ["block present → rules armed; absent → both rules off"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-TEST-001
      title: Rule tests (TDD policy families)
      requirements: [SC-1, SC-2, SC-3]
      depends_on: [TASK-LINTER-001]
      files: { create: [], modify: [tools/spec-linter/tests/test_build_report_contract.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): TDD policy coverage" }
      acceptance: ["≥8 tests across the two families + legacy silences"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_build_report_contract.py -q"
    - id: TASK-TEST-002
      title: CLI tests (block present/absent)
      requirements: [SC-3]
      depends_on: [TASK-LINTER-002]
      files: { create: [], modify: [tools/spec-linter/tests/test_cli.py], tests: [tools/spec-linter/tests/test_cli.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): tdd_policy CLI coverage" }
      acceptance: ["high+off exit 1; absent block → exit 0 same doc"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_cli.py -q"
    - id: TASK-SKILL-001
      title: sdd-build effective-mode + --no-tdd + RED validity
      requirements: [MUST-2, MUST-3]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-build/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: docs, commit: "docs(sdd): risk-driven TDD conduct" }
      acceptance: ["derivation rule, --no-tdd constraints, §10.2 RED validity present"]
      verification:
        green: "grep -q 'no-tdd' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-CMD-001
      title: /build --no-tdd flag surface
      requirements: [SHOULD-1]
      depends_on: [TASK-SKILL-001]
      files: { create: [], modify: [.claude/commands/workflow/build.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs2, commit: "docs(sdd): --no-tdd flag" }
      acceptance: ["flag + constraint table documented"]
      verification:
        green: "grep -q 'no-tdd' .claude/commands/workflow/build.md"
    - id: TASK-TMPL-001
      title: TDD Evidence exception grammar + distinction note
      requirements: [SHOULD-2, MUST-4]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs3, commit: "docs(sdd): TDD exception grammar" }
      acceptance: ["exception row format + new-test/regression/alternative note"]
      verification:
        green: "grep -q 'exception:' .claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
    - id: TASK-TEST-003
      title: Documental anchors
      requirements: [SC-4]
      depends_on: [TASK-CONTRACT-001, TASK-SKILL-001, TASK-CMD-001, TASK-TMPL-001]
      files: { create: [tests/test_tdd_policy.py], modify: [], tests: [tests/test_tdd_policy.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): tdd policy anchors" }
      acceptance: ["block shape, skill/command/template anchors, version history"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_tdd_policy.py -q"
    - id: TASK-DOCS-001
      title: USAGE.md TDD rules addendum
      requirements: [MUST-5]
      depends_on: [TASK-LINTER-002]
      files: { create: [], modify: [tools/spec-linter/USAGE.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs4, commit: "docs(spec-linter): TDD policy rules" }
      acceptance: ["both rules + legacy silences documented"]
      verification:
        green: "grep -q 'tdd_required_by_risk' tools/spec-linter/USAGE.md"
```

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Modify | `tdd_policy` block + v3.11.0 + history | (general) | None |
| 2 | `tools/spec-linter/spec_linter/contracts/build_report.py` | Modify | `BR.tdd_required_by_risk` + `BR.tdd_exception_invalid` | @python-developer | 1 |
| 3 | `tools/spec-linter/spec_linter/cli.py` | Modify | Pass tdd_policy params; absent block → rules off | @python-developer | 2 |
| 4 | `tools/spec-linter/tests/test_build_report_contract.py` | Modify | ≥8 rule tests | @test-generator | 2 |
| 5 | `tools/spec-linter/tests/test_cli.py` | Modify | Block present/absent CLI tests | @test-generator | 3 |
| 6 | `.claude/skills/sdd-build/SKILL.md` | Modify | Effective mode, --no-tdd, RED validity | (general) | 1 |
| 7 | `.claude/commands/workflow/build.md` | Modify | --no-tdd flag surface | (general) | 6 |
| 8 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Exception grammar + distinction note | (general) | 1 |
| 9 | `tests/test_tdd_policy.py` | Create | Documental anchors | @test-generator | 1, 6, 7, 8 |
| 10 | `tools/spec-linter/USAGE.md` | Modify | Rules documentation | (general) | 3 |

**Total Files:** 10

**`tdd_policy` block (file 1, exact shape):**

```yaml
tdd_policy:
  effective_mode_rule: "strongest of: --tdd flag (opt-in), risk_policy[risk level], any manifest task with execution.tdd == required"
  risk_policy:
    low: recommended
    medium: required_for_logic
    high: required
    critical: required
  no_tdd_flag:
    dispenses: [low, medium]
    requires: recorded_justification
    never: [high, critical]
  exception_categories: [non_executable_documentation, declarative_configuration, generated_artifact, vendored_content, infrastructure_declaration]
  red_validity: "a broken RED command, an unrelated import error, or a pre-existing failure is not RED evidence"
  enforcement:
    high_critical_off: FAIL
    medium_off: WARN
    low_off: silent
    no_risk_row: silent   # pre-Increment-2 reports — adoption path
```

---

## Agent Assignment Rationale

| Agent | Files | Citation (routing.json) |
|-------|-------|-------------------------|
| @python-developer | 2, 3 | "Python code architect … clean patterns, type hints", kb [python, pydantic, testing] |
| @test-generator | 4, 5, 9 | "Test automation expert for Python … pytest" |
| (general) | 1, 6, 7, 8, 10 | Skill citation: `component-model` — policy edits fully specified here |

---

## Code Patterns

### Pattern 1: Rule wiring (extend, don't fork)

```python
def _check_tdd_required_by_risk(self, parsed) -> list[Finding]:
    if not self._risk_tdd_policy:
        return []
    raw = parsed.metadata.get("risk level")
    if raw is None:
        return []                       # pre-Inc2 report — adoption path
    level = raw.split()[0].lower() if raw.split() else ""
    obligation = self._risk_tdd_policy.get(level)
    mode = (parsed.metadata.get("tdd mode") or "").strip().lower()
    if mode != "off" or obligation is None:
        return []
    if obligation == "required":
        return [Finding(level=Level.FAIL, rule="BR.tdd_required_by_risk", ...)]
    if obligation == "required_for_logic":
        return [Finding(level=Level.WARN, rule="BR.tdd_required_by_risk", ...)]
    return []
```

### Pattern 2: Exception scan

```python
_EXCEPTION = re.compile(r"exception:\s*([a-z0-9_]+)", re.IGNORECASE)
# scan the TDD Evidence section text; every captured token must be a known category
```

### Template grammar (file 8)

```markdown
| {task} | n/a — exception: non_executable_documentation; verified by: markdownlint docs/ | - | - | - |
```

---

## Data Flow

```text
1. sdd-build derives effective mode (flag · risk_policy[level] · task tdd) → TDD Mode row
2. --no-tdd: honored only at low/medium with justification; refused+recorded at high/critical
3. spec-lint --phase build: risk-vs-mode floor + exception-category validation
4. Ship/Gate S re-run the same gate (fail-mode under /auto)
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
| Unit (rules) | high/critical FAIL · medium WARN · low/legacy silent · exception valid/invalid | file 4 | pytest mutator | AT-001…AT-008; ≥8 tests |
| Integration (CLI) | Armed vs absent-block behavior | file 5 | cli.main | AT-001 + fallback |
| Contract (documental) | Block shape, skill/command/template anchors, history | file 9 | pytest | AT-009 |
| Parity | Post-repackage | existing | pytest | AT-010 |
| E2E (dogfood) | This run's own report: Risk Level medium + TDD Mode off → live WARN, non-blocking | gate runs | - | AT-003 live |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `tdd_policy` block absent | Both rules off — older contracts files unchanged | No |
| Block present, malformed subkeys | `_OperationalError` → exit 2 | No |
| Unknown Risk Level token | Rules silent (vocabulary validation is the define phase's RP surface) | No |
| Unknown exception category | `BR.tdd_exception_invalid` FAIL | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `tdd_policy.risk_policy` | map | §8.3 TDD row | level → obligation |
| `tdd_policy.no_tdd_flag` | map | low/medium only + justification | --no-tdd constraints |
| `tdd_policy.exception_categories` | list | 5 categories | Sanctioned exception tokens |
| `tdd_policy.enforcement` | map | FAIL/WARN/silent split | Severity assignment (documented AND wired — read by cli.py) |

---

## Security Considerations

- Fail-closed only where both opt-in markers exist (schema v2 + Risk Level row); no retroactive blocking.
- Linter never executes RED/GREEN commands — declared-evidence validation only.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Findings | Rules name the level, obligation, and offending token verbatim |
| Adoption | Legacy silences are explicit code paths with tests, not accidents |

---

## Pipeline Architecture (if applicable)

Not applicable.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial version — 4 [ASSUMED] decisions (≥ 0.85), 10-task v2 manifest |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_RISK_DRIVEN_TDD.md`
