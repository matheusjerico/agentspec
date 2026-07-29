# DESIGN: Risk Profiles

> Technical design for the machine-readable risk profile: contract data in WORKFLOW_CONTRACTS.yaml, a Define-phase linter contract with WARN-only risk rules, template/skill propagation Define → Design → Build, all in Observe/Warn mode.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_PROFILES |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_RISK_PROFILES.md](./DEFINE_RISK_PROFILES.md) |
| **Status** | Ready for Build |
| **Risk Level** | medium (echo from DEFINE — reasons: new warn-only linter logic, limited blast radius) |
| **Design Confidence** | 0.90 — KB patterns (`python`, `testing`) + specialist matches; Increment 1 precedents reused |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                RISK PROFILES — SYSTEM DIAGRAM (Observe/Warn)          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DEFINE_{F}.md                                                       │
│   ## Risk Profile          sdd-define step: score 5 dimensions,      │
│   ```yaml                  level = max(dimensions) + elevation       │
│   risk_profile: ...        floors; override needs author+rationale   │
│   ```                                                                │
│        │                                                             │
│        ▼                                                             │
│  spec-lint --phase define                                            │
│   └─ DefinePhaseContract (new)                                       │
│      = SddPhaseContract section rules (FAIL, unchanged)              │
│      + RP.* rules (ALL Level.WARN — exit stays 0):                   │
│        RP.profile_missing → "effective level medium"                 │
│        RP.level_invalid / RP.dimension_invalid                       │
│        RP.override_unjustified                                       │
│        RP.level_below_dimensions (max-rule check)                    │
│      params ← WORKFLOW_CONTRACTS.yaml risk_profiles block            │
│        │                                                             │
│        ▼                                                             │
│  DESIGN_{F}.md  Metadata "Risk Level" row = ECHO (never recomputed)  │
│  BUILD_REPORT   Metadata "Risk Level" row (optional, additive)       │
│                                                                      │
│  CRITICAL halt: unchanged, fail-closed; override can never remove it │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `risk_profiles` contract block | Levels, dimensions, elevation rules, override requirements, legacy default — the WHAT as data | YAML in `WORKFLOW_CONTRACTS.yaml` |
| `DefinePhaseContract` | Define-phase contract: section presence (FAIL, reused semantics) + `RP.*` warn rules parsing the Risk Profile YAML fence | Python 3.12, `Contract` protocol, mirrors `BuildReportContract` precedent |
| CLI routing | `--phase define` routes to `DefinePhaseContract` when the `risk_profiles` block exists; falls back to plain `SddPhaseContract` otherwise (older contracts files keep working) | `cli.py` |
| Template propagation | DEFINE gains `## Risk Profile` (YAML fence); DESIGN gains `Risk Level` metadata row (echo); BUILD_REPORT gains optional `Risk Level` row | Markdown templates |
| Skill steps | sdd-define derives the profile (rules from the contract block); sdd-design copies level+reasons verbatim | Skill markdown |

---

## Key Decisions

### Decision 1: A dedicated `DefinePhaseContract`, mirroring the BuildReportContract precedent `[ASSUMED 0.90]`

**Context:** WARN-level risk rules must coexist with the FAIL-only generic section check (DEFINE A-001).

**Choice:** New `spec_linter/contracts/define_phase.py` implementing the `Contract` protocol: runs the same section-presence rules as `SddPhaseContract` (FAIL, rule id `L2.required_section`) plus `RP.*` rules capped at `Level.WARN`. CLI routes `--phase define` to it when the contracts file carries a `risk_profiles` block.

**Alternatives rejected:** (1) warn-layer bolted onto `SddPhaseContract` — pollutes the generic contract used by design/iterate; (2) second lint pass — two verdicts per artifact, rejected in Increment 1 for the same reason.

**Consequences:** one more phase-specific contract module; the pattern is now established (build, define) for future phase semantics. Fallback keeps plugin/older layouts green.

### Decision 2: Profile as a fenced YAML block inside `## Risk Profile` `[ASSUMED 0.85]`

**Context:** DEFINE A-003 — the linter must parse the profile deterministically.

**Choice:** First ```yaml fence within the `## Risk Profile` section (section = `##`-level scoping, single heading vocabulary per Increment 1's round-2 lesson), `yaml.safe_load`, expect top-level `risk_profile` mapping. Unparseable YAML → `RP.profile_missing` WARN (Observe mode never blocks on malformed input).

**Alternatives rejected:** Markdown table — loses nesting (dimensions + override), diverges from the plan §8.1 model verbatim.

### Decision 3: Elevation rules as data with `floor` semantics `[ASSUMED 0.90]`

**Context:** Plan §8.2 — the contract must not depend on free model judgment.

**Choice:** `risk_profiles.elevation_rules` — a list of `{trigger, floor}` entries (auth/authz → high; destructive migration → critical; production write w/o rollback → critical; new endpoint w/o sensitive data → medium; documentation-only → typical low). `level = max(max(dimension values), max(applicable floors))`. The skill applies triggers (semantic matching is the model's job); the linter mechanically checks `level >= max(dimension values)` (`RP.level_below_dimensions`) — floors are skill-applied, dimension-consistency is linter-checked.

**Consequences:** the deterministic core (max rule) is machine-verified; trigger applicability stays human/model-auditable via `reasons`.

### Decision 4: All `RP.*` findings are `Level.WARN` in this increment `[ASSUMED 0.95]`

**Context:** Plan §17.2 Observe→Warn→Enforce; §18 PR 2 scope. Only the pre-existing CRITICAL halt is fail-closed, and it is untouched.

**Choice:** `RP.*` rules hard-cap at WARN (exit 0). `define.required_sections` NOT extended. The `risk_profiles.rollout: observe_warn` key records the mode; flipping to Enforce later is a contract-data change plus severity bump — a future, versioned increment.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Modify | Add `risk_profiles` block (levels, dimensions, dimension_values, elevation_rules, override, legacy, rollout); version 3.9.0 + history | (general) | None |
| 2 | `tools/spec-linter/spec_linter/contracts/define_phase.py` | Create | `DefinePhaseContract` — sections (FAIL) + `RP.*` (WARN): profile_missing, level_invalid, dimension_invalid, override_unjustified, level_below_dimensions | @python-developer | 1 |
| 3 | `tools/spec-linter/spec_linter/cli.py` | Modify | Route `--phase define` → `DefinePhaseContract` when `risk_profiles` present; else existing `SddPhaseContract` path | @python-developer | 2 |
| 4 | `tools/spec-linter/tests/test_define_phase_contract.py` | Create | Rule tests: ≥1 clean-PASS + ≥1 WARN path per `RP.*` rule; exit-semantics (WARN → PASS-level 0 exit) | @test-generator | 2 |
| 5 | `tools/spec-linter/tests/test_cli.py` | Modify (append) | CLI: valid profile → exit 0 no RP findings; missing profile → exit 0 with WARN; contracts file without `risk_profiles` → plain section behavior | @test-generator | 3 |
| 6 | `.claude/sdd/templates/DEFINE_TEMPLATE.md` | Modify | `## Risk Profile` section with the §8.1 YAML model + derivation note | (general) | 1 |
| 7 | `.claude/skills/sdd-define/SKILL.md` | Modify | New step: score dimensions, apply max + elevation floors from the contract block, record reasons; override obligations; legacy note | (general) | 1 |
| 8 | `.claude/sdd/templates/DESIGN_TEMPLATE.md` | Modify | Metadata `Risk Level` row (echo, never recompute) | (general) | 1 |
| 9 | `.claude/skills/sdd-design/SKILL.md` | Modify | Step 1 obligation: copy level + reasons from DEFINE into the DESIGN metadata echo | (general) | 1 |
| 10 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Optional `Risk Level` metadata row (additive; absence not a finding this increment) | (general) | 1 |
| 11 | `tests/test_risk_profiles.py` | Create | Documental anchors: block shape (4 levels/5 dimensions/≥5 rules), template markers, skill anchors, halt-invariant text, rollout=observe_warn | @test-generator | 1, 6, 7, 8, 9, 10 |
| 12 | `tools/spec-linter/USAGE.md` | Modify | Document define-phase risk warn rules + fallback behavior | (general) | 3 |

**Total Files:** 12. (`build-plugin.sh` unchanged — parity auto-globs the new `.py`; Step 5e already guards packaging.)

**`risk_profiles` block (file 1, exact shape):**

```yaml
risk_profiles:
  rollout: observe_warn          # Enforce is a future, versioned change (plan §17.2)
  levels: [low, medium, high, critical]
  dimensions: [data_loss, security, reversibility, blast_radius, migration]
  dimension_values: [none, low, medium, high, critical]
  derivation: "level = max(dimension values), raised to any applicable elevation floor"
  elevation_rules:
    - trigger: "authentication or authorization change"
      floor: high
    - trigger: "destructive migration"
      floor: critical
    - trigger: "production write without rollback"
      floor: critical
    - trigger: "new endpoint without sensitive data"
      floor: medium
    - trigger: "documentation-only change"
      typical: low
  override:
    required_fields: [author, rationale]
    invariant: "an override never removes the CRITICAL halt"
  legacy:
    effective_level: medium
    mode: WARN                   # never a silent low (plan §8.5)
```

---

## Agent Assignment Rationale

> Citations against `.claude/skills/agent-router/routing.json` per specialist-autoprovision. No gaps; no provisioning events.

| Agent | Files Assigned | Citation (routing.json) |
|-------|----------------|-------------------------|
| @python-developer | 2, 3 | "Python code architect … clean patterns, dataclasses, type hints", `kb_domains: [python, pydantic, testing]` |
| @test-generator | 4, 5, 11 | "Test automation expert for Python. Generates pytest unit tests, integration tests, and fixtures", `kb_domains: […, testing]` |
| (general) | 1, 6, 7, 8, 9, 10, 12 | Skill citation: `component-model` (layer governance) — policy YAML/markdown edits fully specified here |

---

## Code Patterns

### Pattern 1: Contract class (mirrors `BuildReportContract`; single `##` heading vocabulary)

```python
_H2 = re.compile(r"^##\s+(.*\S)\s*$", re.MULTILINE)
_YAML_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)

class DefinePhaseContract:
    def __init__(self, required_sections: list[str], levels: list[str],
                 dimensions: list[str], dimension_values: list[str],
                 override_required: list[str], legacy_level: str) -> None:
        self.name = "sdd-phase:define"
        ...
    def parse(self, artifact: str) -> _ParsedDefine: ...   # frozen, slots
    def check(self, parsed: _ParsedDefine) -> list[Finding]: ...
```

### Pattern 2: WARN finding (severity cap is the contract's choice)

```python
Finding(
    level=Level.WARN,
    rule="RP.profile_missing",
    field="Risk Profile",
    message="no parseable risk profile — effective level 'medium' assumed (observe/warn rollout); add the Risk Profile section per DEFINE_TEMPLATE.md",
    expected="risk_profile YAML block",
    found="absent",
)
```

### Pattern 3: Max-rule check (values ordered by index in `dimension_values`)

```python
rank = {v: i for i, v in enumerate(self._dimension_values)}   # none < low < ... < critical
declared = rank.get(profile.get("level"))
max_dim = max((rank[v] for v in dims.values() if v in rank), default=0)
if declared is not None and declared < max_dim:
    findings.append(...)  # RP.level_below_dimensions, WARN
```

### Pattern 4: CLI fallback (older contracts files stay green)

```python
if phase == "define" and isinstance(data.get("risk_profiles"), dict):
    contract = _define_phase_contract(data, contracts_file)
else:
    contract = SddPhaseContract(phase, required)   # unchanged for every other case
```

### Template shape (file 6 — DEFINE_TEMPLATE addition)

````markdown
## Risk Profile

> Derived in Phase 1 (sdd-define): level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).
> Overrides require author + rationale and never remove the CRITICAL halt.

```yaml
risk_profile:
  level: {low / medium / high / critical}
  reasons:
    - "{why this level — cite the dimension or elevation rule}"
  dimensions:
    data_loss: {none / low / medium / high / critical}
    security: {none / low / medium / high / critical}
    reversibility: {none / low / medium / high / critical}
    blast_radius: {none / low / medium / high / critical}
    migration: {none / low / medium / high / critical}
  override:
    applied: false
    author: null
    rationale: null
```
````

---

## Data Flow

```text
1. sdd-define scores dimensions → derives level (max + floors) → writes the
   Risk Profile section with reasons
2. spec-lint --phase define validates: sections (FAIL rules, unchanged) +
   RP.* (WARN only; missing profile ⇒ "effective medium" warn)
3. sdd-design copies level + reasons into the DESIGN "Risk Level" metadata row
4. sdd-build (optional this increment) carries the row into BUILD_REPORT
5. Increments 4–5 later key TDD/Task-Review policy on the level — out of scope here
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
| Unit (rules) | Each `RP.*` rule: clean-PASS + WARN path | `tools/spec-linter/tests/test_define_phase_contract.py` | pytest, fixture+mutator | AT-001…AT-005, AT-007; ≥10 tests |
| Integration (CLI) | Exit codes: WARN ⇒ exit 0; fallback without `risk_profiles` block | `tools/spec-linter/tests/test_cli.py` | pytest `main(argv)` | AT-001/002/005 + fallback |
| Contract (documental) | Block shape, templates, skills, halt invariant, rollout mode | `tests/test_risk_profiles.py` | pytest YAML/substring | AT-006, AT-008, AT-009 |
| Parity | Canonical ↔ plugin after repackage | existing `tests/test_plugin_parity.py` + Step 5e | pytest | AT-010 |
| E2E (dogfood) | This DEFINE's own prospective profile lints clean post-build | spec-lint run | - | AT-001 live |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Malformed YAML in the profile fence | `RP.profile_missing` WARN (observe mode never blocks) | No |
| `risk_profiles` block absent from contracts file | Silent fallback to plain `SddPhaseContract` (backward compatible by design) | No |
| Unknown dimension key / value | `RP.dimension_invalid` WARN naming the allowed sets | No |
| Section rules (existing) | Unchanged FAIL semantics — exit 1 as today | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `risk_profiles.rollout` | enum | `observe_warn` | Records the rollout phase; Enforce is a future versioned change |
| `risk_profiles.levels` / `dimensions` / `dimension_values` | lists | §8.1 sets | Allowed vocabularies for `RP.*` validation |
| `risk_profiles.elevation_rules` | list | 5 rules | Floors applied by sdd-define; anchored by tests |
| `risk_profiles.legacy.effective_level` / `.mode` | str | `medium` / `WARN` | Legacy default — never silent low |

---

## Security Considerations

- No new blocking behavior; the only fail-closed path (CRITICAL halt) is untouched and its non-override invariant is recorded as contract data + anchored by test.
- Linter remains deterministic, local, no model calls, no secrets.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Findings | Existing Verdict rendering; `RP.*` warns visible on stdout with migration guidance |
| Rollout state | `risk_profiles.rollout` key is greppable/testable; flipping it is a versioned contract change |

---

## Pipeline Architecture (if applicable)

Not applicable — no data pipelines.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial version — 4 [ASSUMED] decisions (all ≥ 0.85), 12-file manifest, RP rule inventory |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_RISK_PROFILES.md`
