# DESIGN: Task Manifest

> Technical design for the executable task manifest v2: schema as contract data, a DesignPhaseContract with FAIL-level TM.* graph rules for adopters, template/skill integration, and byte-identical v1 behavior.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TASK_MANIFEST |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_TASK_MANIFEST.md](./DEFINE_TASK_MANIFEST.md) |
| **Risk Level** | medium (echo from DEFINE — blast_radius medium: design-lint path + two skills; no elevation floor) |
| **Status** | ✅ Complete (Built) |
| **Design Confidence** | 0.90 — third phase-contract of the established pattern; KB `python`/`testing` |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│              TASK MANIFEST v2 — SYSTEM DIAGRAM                        │
├──────────────────────────────────────────────────────────────────────┤
│  DESIGN_{F}.md                                                       │
│   ## Task Manifest (v2)     sdd-design step: derive tasks from the   │
│   ```yaml                   file manifest — verifiable changes,      │
│   task_manifest:            DAG, write-sets, verification commands   │
│     manifest_version: 2                                              │
│     tasks: [...]                                                     │
│   ```                                                                │
│        │                                                             │
│        ▼                                                             │
│  spec-lint --phase design                                            │
│   └─ DesignPhaseContract (new)                                       │
│      = section presence (#{1,6}, byte-identical to SddPhaseContract) │
│      + TM.* rules (FAIL for adopters; absent manifest ⇒ 0 findings): │
│        TM.unparseable · TM.duplicate_id · TM.cycle                   │
│        TM.unknown_dependency · TM.write_conflict                     │
│        TM.missing_verification · TM.missing_requirements (WARN)      │
│      params ← WORKFLOW_CONTRACTS.yaml task_manifest block            │
│        │                                                             │
│        ▼                                                             │
│  sdd-build: v2 present → consume graph (NO inference), topo order,   │
│  task_id per row in BUILD_REPORT (new Task ID column);               │
│  no manifest → today's inference, manifest_version: 1 recorded       │
│                                                                      │
│  Parallel DISPATCH stays sequential — Increment 7 owns scheduling.   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `task_manifest` contract block | Schema vocabularies as data: required task fields, files keys, verification keys, manifest_version | YAML in `WORKFLOW_CONTRACTS.yaml` (v3.10.0) |
| `DesignPhaseContract` | Section presence (any-level, unchanged semantics) + TM.* graph validation of the v2 manifest | Python 3.12, `Contract` protocol, stdlib graph checks (Kahn/DFS + set intersection) |
| CLI routing | `--phase design` → DesignPhaseContract when the block exists; silent fallback otherwise | `cli.py`, mirrors define/build routing |
| Template/skill integration | DESIGN Task Manifest section; sdd-design derivation step + size budget; sdd-build v2 consumption; BUILD_REPORT Task ID column | Markdown |

---

## Key Decisions

### Decision 1: Third phase-contract of the established pattern `[ASSUMED 0.90]`

**Context:** TM.* rules need a design-phase home; two precedents exist (BuildReportContract, DefinePhaseContract).

**Choice:** `spec_linter/contracts/design_phase.py` — presence rules byte-identical to `SddPhaseContract` (`#{1,6}` vocabulary — Increment 2's Critical lesson applied from the start), manifest scan `##`-only prefix-matched (`task_manifest` section slug starts with `task_manifest`), CLI-routed with silent fallback when the contracts file lacks the block.

**Alternatives rejected:** composing SddPhaseContract internally — indirection without benefit; the local duplication of two small helpers is the established, reviewed pattern.

### Decision 2: FAIL severity for adopters; silence for v1 `[ASSUMED 0.90]`

**Context:** Plan §9.5 is explicit ("cycles and duplicate IDs block Design"); rollout §17.2 asks Observe→Warn→Enforce for changes affecting existing artifacts.

**Choice:** A *present* v2 manifest gets FAIL-level structural rules (opt-in artifact — adopters get the contract they opted into; Increment 1 precedent with schema-v2 reports). An *absent* manifest yields zero TM findings — v1 designs behave byte-identically. `TM.missing_requirements` alone is WARN (traceability is Increment 6's job).

**Consequences:** no ramp needed; the fail-closed set is exactly the graph-integrity family a broken plan cannot survive.

### Decision 3: Unparseable manifest is FAIL, unlike the risk profile's WARN `[ASSUMED 0.85]`

**Context:** Increment 2 treated malformed profile YAML as `RP.profile_missing` WARN.

**Choice:** `TM.unparseable` FAIL. The two artifacts differ in kind: a risk profile is advisory metadata under Observe/Warn; an executable manifest is the build's execution plan — a plan that cannot parse must not reach Build half-read.

### Decision 4: Graph checks with stdlib only `[ASSUMED 0.90]`

**Choice:** duplicate ids via seen-set; unknown deps via id-set membership; cycles via Kahn's algorithm (unprocessed remainder = cycle members, named in the finding); write conflicts via pairwise `create ∪ modify` intersection within each `parallel_group`. No new dependencies (DEFINE A-002).

---

## Task Manifest (v2)

> Dogfood (DEFINE A-005): this design's own manifest, in the schema it ships. Validated by the rules it delivers at ship-time re-lint (the rules land within this build).

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: task_manifest block + v3.10.0 history in WORKFLOW_CONTRACTS.yaml
      requirements: [MUST-7]
      depends_on: []
      files:
        create: []
        modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml]
        tests: []
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: off, parallel_group: contract, commit: "feat(sdd): task_manifest contract data" }
      acceptance: ["yaml.safe_load exposes task_manifest vocabularies"]
      verification:
        green: "python3 -c 'import yaml; yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"task_manifest\"]'"
        regression: "rtk proxy python3 -m pytest tests/ -q --ignore=tests/test_plugin_parity.py"
    - id: TASK-LINTER-001
      title: DesignPhaseContract with TM.* rules
      requirements: [MUST-3]
      depends_on: [TASK-CONTRACT-001]
      files:
        create: [tools/spec-linter/spec_linter/contracts/design_phase.py]
        modify: []
        tests: []
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: off, parallel_group: linter, commit: "feat(spec-linter): DesignPhaseContract" }
      acceptance: ["valid manifest → 0 TM findings", "cycle/dup/unknown/conflict/unparseable/missing-verification → FAIL"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-LINTER-002
      title: CLI design-phase routing + fallback
      requirements: [MUST-3, SHOULD-1]
      depends_on: [TASK-LINTER-001]
      files:
        create: []
        modify: [tools/spec-linter/spec_linter/cli.py]
        tests: []
      owner: "@python-developer"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: off, parallel_group: linter, commit: "feat(spec-linter): route --phase design" }
      acceptance: ["block present → DesignPhaseContract; absent → byte-identical fallback"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/ -q"
    - id: TASK-TEST-001
      title: Rule tests for DesignPhaseContract
      requirements: [SC-1]
      depends_on: [TASK-LINTER-001]
      files:
        create: [tools/spec-linter/tests/test_design_phase_contract.py]
        modify: []
        tests: [tools/spec-linter/tests/test_design_phase_contract.py]
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: tests, commit: "test(spec-linter): TM rule coverage" }
      acceptance: ["≥12 tests; PASS+FAIL path per family"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_design_phase_contract.py -q"
    - id: TASK-TEST-002
      title: CLI tests for design phase
      requirements: [SC-1, SC-2]
      depends_on: [TASK-LINTER-002]
      files:
        create: []
        modify: [tools/spec-linter/tests/test_cli.py]
        tests: [tools/spec-linter/tests/test_cli.py]
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: tests, commit: "test(spec-linter): design-phase CLI coverage" }
      acceptance: ["valid → 0; blocking family → 1; no block in contracts → fallback"]
      verification:
        green: "cd tools/spec-linter && rtk proxy python3 -m pytest tests/test_cli.py -q"
    - id: TASK-TMPL-001
      title: DESIGN template Task Manifest section + sdd-design derivation step
      requirements: [MUST-1, MUST-2, SHOULD-2]
      depends_on: [TASK-CONTRACT-001]
      files:
        create: []
        modify: [.claude/sdd/templates/DESIGN_TEMPLATE.md, .claude/skills/sdd-design/SKILL.md]
        tests: []
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: docs, commit: "docs(sdd): task manifest v2 in design phase" }
      acceptance: ["template carries the v2 schema; skill owns derivation + size budget"]
      verification:
        green: "grep -q 'task_manifest' .claude/sdd/templates/DESIGN_TEMPLATE.md"
    - id: TASK-TMPL-002
      title: sdd-build v2 consumption + BUILD_REPORT Task ID column
      requirements: [MUST-5, MUST-6]
      depends_on: [TASK-CONTRACT-001]
      files:
        create: []
        modify: [.claude/skills/sdd-build/SKILL.md, .claude/sdd/templates/BUILD_REPORT_TEMPLATE.md]
        tests: []
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: docs2, commit: "docs(sdd): build consumes task manifest v2" }
      acceptance: ["v2 → no inference, topo order, task_id recorded; v1 → unchanged"]
      verification:
        green: "grep -q 'manifest_version' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-TEST-003
      title: Documental anchors for the increment
      requirements: [SC-4, SC-5]
      depends_on: [TASK-CONTRACT-001, TASK-TMPL-001, TASK-TMPL-002]
      files:
        create: [tests/test_task_manifest.py]
        modify: []
        tests: [tests/test_task_manifest.py]
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: tests, commit: "test(sdd): task manifest documental anchors" }
      acceptance: ["block shape, template markers, skill anchors, version history"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_task_manifest.py -q"
    - id: TASK-DOCS-001
      title: USAGE.md design-phase TM documentation
      requirements: [MUST-3]
      depends_on: [TASK-LINTER-002]
      files:
        create: []
        modify: [tools/spec-linter/USAGE.md]
        tests: []
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: off, parallel_group: docs3, commit: "docs(spec-linter): design-phase TM rules" }
      acceptance: ["TM.* inventory + fallback documented"]
      verification:
        green: "grep -q 'DesignPhaseContract' tools/spec-linter/USAGE.md"
```

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Modify | `task_manifest` block (vocabularies as data) + v3.10.0 + history | (general) | None |
| 2 | `tools/spec-linter/spec_linter/contracts/design_phase.py` | Create | DesignPhaseContract — presence `#{1,6}` + TM.* rules | @python-developer | 1 |
| 3 | `tools/spec-linter/spec_linter/cli.py` | Modify | Route `--phase design` with silent fallback | @python-developer | 2 |
| 4 | `tools/spec-linter/tests/test_design_phase_contract.py` | Create | ≥12 rule tests | @test-generator | 2 |
| 5 | `tools/spec-linter/tests/test_cli.py` | Modify (append) | Design-phase CLI + fallback tests | @test-generator | 3 |
| 6 | `.claude/sdd/templates/DESIGN_TEMPLATE.md` | Modify | Task Manifest (v2) section | (general) | 1 |
| 7 | `.claude/skills/sdd-design/SKILL.md` | Modify | Derivation step + size budget + gate item | (general) | 1 |
| 8 | `.claude/skills/sdd-build/SKILL.md` | Modify | v2 consumption branch (no inference, topo order, task_id) | (general) | 1 |
| 9 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Task ID column in Task Execution table | (general) | 1 |
| 10 | `tests/test_task_manifest.py` | Create | Documental anchors | @test-generator | 1, 6, 7, 8, 9 |
| 11 | `tools/spec-linter/USAGE.md` | Modify | Design-phase TM documentation | (general) | 3 |

**Total Files:** 11

**`task_manifest` block (file 1, exact shape):**

```yaml
task_manifest:
  manifest_version: 2
  adoption: "opt-in — a DESIGN without the block is v1: zero TM findings, Build infers as today"
  required_task_fields: [id, title, files, verification]
  files_keys: [create, modify, tests]
  verification_keys: [red, green, regression]
  rules:
    blocking: [unparseable, duplicate_id, cycle, unknown_dependency, write_conflict, missing_verification]
    advisory: [missing_requirements]   # traceability matrix is Increment 6
  write_conflict: "same parallel_group with intersecting create+modify sets"
```

---

## Agent Assignment Rationale

> Citations against `.claude/skills/agent-router/routing.json` (specialist-autoprovision). No gaps.

| Agent | Files Assigned | Citation (routing.json) |
|-------|----------------|-------------------------|
| @python-developer | 2, 3 | "Python code architect … clean patterns, dataclasses, type hints", `kb_domains: [python, pydantic, testing]` |
| @test-generator | 4, 5, 10 | "Test automation expert for Python … pytest unit tests, integration tests, and fixtures" |
| (general) | 1, 6, 7, 8, 9, 11 | Skill citation: `component-model` — policy YAML/markdown fully specified here |

---

## Code Patterns

### Pattern 1: Parsed manifest + graph checks (stdlib)

```python
@dataclass(frozen=True, slots=True)
class _ParsedDesignPhase:
    headings: set[str]
    manifest: dict | None          # task_manifest mapping, None when absent
    manifest_broken: bool          # fence present but unparseable → TM.unparseable

def _cycle_members(tasks: dict[str, list[str]]) -> list[str]:
    indegree = {t: 0 for t in tasks}
    for deps in tasks.values():
        for d in deps:
            if d in indegree:
                indegree[d] += 1
    queue = [t for t, n in indegree.items() if n == 0]
    seen = 0
    while queue:
        seen += 1
        for d in tasks[queue.pop()]:
            if d in indegree:
                indegree[d] -= 1
                if indegree[d] == 0:
                    queue.append(d)
    return sorted(t for t, n in indegree.items() if n > 0) if seen < len(tasks) else []
```

### Pattern 2: Write-conflict detection

```python
groups: dict[str, list[tuple[str, set[str]]]] = {}
for task in tasks:
    group = (task.get("execution") or {}).get("parallel_group")
    writes = set(files.get("create", [])) | set(files.get("modify", []))
    if group:
        for other_id, other_writes in groups.setdefault(group, []):
            overlap = writes & other_writes
            if overlap:
                findings.append(...)  # TM.write_conflict naming both ids + files
        groups[group].append((task_id, writes))
```

### Pattern 3: Presence semantics (Increment 2's lesson, applied from birth)

```python
_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$", re.MULTILINE)   # presence — byte-identical to SddPhaseContract
_H2 = re.compile(r"^##\s+(.*\S)\s*$", re.MULTILINE)            # manifest section scan only (FAIL rules but opt-in artifact)
```

### Pattern 4: CLI routing (same shape as define)

```python
elif phase == "design" and isinstance(data.get("task_manifest"), dict):
    contract = _design_phase_contract(data, contracts_file)
```

---

## Data Flow

```text
1. sdd-design derives tasks from the file manifest → writes the v2 manifest
2. spec-lint --phase design validates: sections (unchanged) + TM.* graph rules
   (absent manifest ⇒ zero TM findings ⇒ v1)
3. sdd-build: v2 → topological execution of declared tasks, task_id recorded
   per row (Task ID column); v1 → today's inference, manifest_version: 1 noted
4. Increments 5/7 later key review and scheduling on task_id/reviewer/parallel_group
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
| Unit (rules) | Each TM.* family PASS+FAIL | file 4 | pytest fixture+mutator | AT-001…AT-006, AT-008; ≥12 tests |
| Integration (CLI) | Exit codes + fallback | file 5 | `cli.main(argv)` | AT-001/002/007 + fallback |
| Contract (documental) | Block shape, templates, skills, version history | file 10 | pytest YAML/substring | AT-009 + SC-5 |
| Parity | Canonical ↔ plugin post-repackage | existing infra | pytest | AT-010 |
| E2E (dogfood) | This DESIGN's own v2 manifest re-linted at ship time | spec-lint | - | AT-001 live |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Manifest fence present, YAML malformed | `TM.unparseable` FAIL (Decision 3) | No |
| Manifest absent | Zero TM findings — v1 (never a WARN: v1 is a supported mode, not a migration gap) | No |
| `task_manifest` contracts block absent | Silent fallback to plain SddPhaseContract | No |
| Block present but malformed subkeys | `_OperationalError` → exit 2 | No |
| Section rules | Unchanged FAIL semantics (`#{1,6}` presence) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `task_manifest.manifest_version` | int | 2 | Version adopters declare |
| `task_manifest.required_task_fields` | list | id, title, files, verification | Per-task shape floor |
| `task_manifest.files_keys` / `verification_keys` | lists | §9.2 sets | Allowed sub-vocabularies |
| `task_manifest.rules.blocking` / `.advisory` | lists | 6 blocking + 1 advisory | Severity assignment as data |

---

## Security Considerations

- Verification commands are DATA validated for presence, never executed by the linter — execution stays in Build under its existing policies.
- No new blocking behavior for v1 artifacts; adopters opt into the fail-closed graph rules by declaring the block.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Findings | TM.* findings name ids, cycle members, and conflicting files verbatim |
| Adoption | `manifest_version` recorded in BUILD_REPORT rows — v1/v2 visible per run |

---

## Pipeline Architecture (if applicable)

Not applicable.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial version — 4 [ASSUMED] decisions (≥ 0.85), 11-file manifest, dogfood v2 task manifest |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_TASK_MANIFEST.md`
