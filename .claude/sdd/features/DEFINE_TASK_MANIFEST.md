# DEFINE: Task Manifest

> Give DESIGN an executable, versioned task manifest (v2) — explicit task graph with dependencies, files, and verification commands, deterministically validated — so Build consumes a plan instead of inferring one; v1 designs keep today's behavior.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TASK_MANIFEST |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 15/15 |

**Source:** `docs/superpowers/plans/2026-07-29-agentspec-incremental-improvements.md` — Increment 3 (§9), PR 3 scope §18 ("versioned schema and v1 adapter"), dependency tree §19. Phase 0 carried by the ratified plan (benchmark evidence §3: Superpowers' smaller, explicit tasks; YAGNI §21). Full parallel-dispatch policy explicitly deferred to Increment 7.

---

## Problem Statement

Build converts a *file* manifest into tasks on the fly (§9.1): dependencies, tests, commit intent, and delegation are inferred at execution time, making runs unpredictable and leaving Increments 5 and 7 (per-task review, parallel/commit policy) with no machine-readable task identity (`task_id`) to key on.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer (Matheus) | Sequences Increments 5–7, which need `task_id`, reviewers, and write-sets as data | No stable task identity exists; late inference makes graphs unreproducible between runs |
| Autopilot runs (`/auto`, `autopilot.sh`) | Autonomous Build delegates and verifies per task | Inferred tasks can't be pre-validated: a cyclic or conflicting plan is discovered mid-build, not at Design |
| Plugin consumers (vendored installs, user projects) | Author DESIGNs with the distributed templates | No way to declare per-task verification commands; Build re-derives intent from prose |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | `DESIGN_TEMPLATE.md` gains a `Task Manifest (v2)` section: fenced YAML `task_manifest` with `manifest_version: 2` and per-task `id`, `title`, `requirements`, `depends_on`, `files {create, modify, tests}`, `owner`, `reviewer`, `risk`, `execution {tdd, parallel_group, commit}`, `acceptance`, `verification {red, green, regression}` (§9.2 model; schema only — full code never copied into the plan, §9.3) |
| **MUST** | `sdd-design` SKILL step: derive tasks from the file manifest — a task is a verifiable change (not necessarily one file); every code-bearing task carries ≥1 requirement reference and ≥1 verification command; dependencies form a DAG |
| **MUST** | Deterministic validation in `spec-lint --phase design` via a new `DesignPhaseContract`: when a v2 manifest is present — duplicate ids, dependency cycles, unknown `depends_on` targets, same-`parallel_group` write-set overlaps, tasks without verification commands, unparseable manifest YAML → FAIL (§9.5 "cycles and duplicate IDs block Design"); section-presence semantics preserved byte-identical to `SddPhaseContract` (Increment 2's lesson) |
| **MUST** | v1 compatibility: a DESIGN without a `task_manifest` block produces ZERO TM findings — Build keeps today's inference behavior and records `manifest_version: 1` in the report |
| **MUST** | `sdd-build` SKILL: v2 manifest present → consume the explicit graph (no task inference), execute in topological order, record `task_id`, agent, tests, and requirements per task in the BUILD_REPORT |
| **MUST** | `BUILD_REPORT_TEMPLATE.md` Task Execution table gains a `Task ID` column (additive; `-` for v1 builds) |
| **MUST** | `task_manifest` contract block in `WORKFLOW_CONTRACTS.yaml` (schema vocabularies as data: required task fields, execution/verification keys, manifest_version 2); version bump + history (§17.1) |
| **SHOULD** | CLI fallback mirrors Increment 2: contracts file without the `task_manifest` block → plain design-phase behavior, byte-identical |
| **SHOULD** | Size-budget guidance in `sdd-design` (§9.3): manifests declare, never embed implementations; exceptionally large designs need a recorded justification |
| **COULD** | `TM.*` WARN when a task's `requirements` list is empty (full traceability matrix is Increment 6) |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] A valid v2 manifest lints with 0 TM findings (exit 0); each blocking family — duplicate id, cycle, unknown dependency, write conflict, missing verification, unparseable manifest — yields FAIL (exit 1), each proven by ≥1 PASS-path and ≥1 FAIL-path test (≥12 rule tests)
- [ ] A DESIGN without a manifest produces 0 TM findings — v1 behavior byte-identical, ≥2 tests (contract + CLI fallback)
- [ ] Section-presence FAIL semantics for the design phase remain byte-identical to `SddPhaseContract` (any-level headings) — ≥1 regression test
- [ ] Build-side consumption anchored: sdd-build v2-vs-v1 branches + BUILD_REPORT Task ID column asserted by ≥3 documental tests
- [ ] `task_manifest` schema vocabularies exist as contract data, asserted verbatim by ≥1 test
- [ ] 0 regressions: spec-linter and root suites green; `./build-plugin.sh` incl. Step 5e parity exit 0

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Valid manifest passes | DESIGN with a well-formed v2 manifest (2+ tasks, DAG, disjoint write-sets) | `spec-lint --phase design` | Exit 0, no TM findings |
| AT-002 | Duplicate id blocks | Two tasks share `id: TASK-A` | Linter runs | Exit 1, `TM.duplicate_id` |
| AT-003 | Cycle blocks | TASK-A depends_on TASK-B depends_on TASK-A | Linter runs | Exit 1, `TM.cycle` |
| AT-004 | Unknown dependency blocks | depends_on names a nonexistent id | Linter runs | Exit 1, `TM.unknown_dependency` |
| AT-005 | Write conflict blocks | Same `parallel_group`, overlapping create/modify sets | Linter runs | Exit 1, `TM.write_conflict` |
| AT-006 | Missing verification blocks | A code task without any `verification` command | Linter runs | Exit 1, `TM.missing_verification` |
| AT-007 | v1 legacy is silent | DESIGN without a `task_manifest` block | Linter runs | Exit 0, zero TM findings |
| AT-008 | Unparseable manifest blocks | Present fence, malformed YAML | Linter runs | Exit 1, `TM.unparseable` (an executable plan that cannot parse is a broken contract — opt-in artifact, fail-closed) |
| AT-009 | Build consumes the graph | sdd-build SKILL + BUILD_REPORT template | Documental tests | v2-no-inference + topological order + Task ID column anchors pass |
| AT-010 | Parity + suites | `./build-plugin.sh` + both suites | Run | Exit 0, all green |

---

## Out of Scope

Explicitly NOT included (plan §18 PR 3, §19, §21):

- Parallel dispatch policy and scheduler semantics — declaring `parallel_group` and validating write conflicts lands now; *dispatching* in parallel is Increment 7
- Per-task review flow (Increment 5) and risk-driven TDD activation (Increment 4) — the `reviewer`/`risk`/`tdd` fields land as declared data only
- Requirement–test traceability matrix (Increment 6) — `requirements` refs land; coverage rules do not
- Commit SHA enforcement and atomic-commit policy (Increment 7) — `execution.commit` is a declared message intent only
- Retrofitting archived DESIGNs to v2 (v1 stays valid indefinitely this increment)
- Increments 4–9 of the program

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical, `plugin/` generated; Step 5e parity must stay green | All edits canonical; repackage before ship |
| Technical | spec-linter deterministic; graph checks are pure data validation | Cycle/conflict detection implemented on the parsed YAML, no model calls |
| Compatibility | v2 is opt-in: blocking rules apply ONLY when a manifest is present (Increment 1 precedent — new schema enforces for adopters, legacy silent) | No Observe/Warn ramp needed for v1 docs; they are untouched |
| Compatibility | Design-phase section FAIL semantics must not change (Increment 2's Critical lesson) | Presence check byte-identical to `SddPhaseContract`; new vocabulary only for manifest scanning |
| Process | Dogfooding (§16.4): this feature runs under `/auto`; its own DESIGN will carry a v2 manifest validated by the rules it ships | The run exercises its own gate |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/` (new contract + tests), `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`, `.claude/sdd/templates/{DESIGN,BUILD_REPORT}_TEMPLATE.md`, `.claude/skills/{sdd-design,sdd-build}/SKILL.md`, `tests/` | Framework/tooling feature |
| **KB Domains** | `python`, `testing` | Graph validation in Python; pytest table-driven rule tests |
| **IaC Impact** | None | Local tooling and documents only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

Not applicable — framework feature; no data pipelines.

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: medium
  reasons:
    - "blast_radius medium: touches the design-phase lint path and both design/build skills"
    - "no elevation floor applies (no auth, no migration, no production write)"
  dimensions:
    data_loss: none
    security: none
    reversibility: low
    blast_radius: medium
    migration: none
  override:
    applied: false
    author: null
    rationale: null
```

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | The DesignPhaseContract can follow the established phase-contract pattern (BuildReportContract, DefinePhaseContract) without engine changes | Engine refactor first — larger scope | [ ] |
| A-002 | Cycle/conflict detection on a parsed YAML graph is tractable with stdlib only (DFS + set intersection; no new dependencies) | Would need a graph library — against repo constraints | [ ] |
| A-003 | The §9.2 field set is sufficient for Increments 4–7 to key on (`tdd`, `reviewer`, `risk`, `parallel_group`, `commit` land as declared data) | Schema v3 later — additive, versioned by `manifest_version` | [ ] |
| A-004 | Blocking-for-adopters (no Observe ramp) is acceptable for a new opt-in artifact, mirroring Increment 1's schema-v2 reports | Would need a WARN mode flag — small contract change | [ ] |
| A-005 | This feature's own DESIGN can carry a valid v2 manifest (dogfood) without circularity — the rules land in the same build the manifest describes | Manifest validated only at ship-time re-lint; acceptable | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §9.1 verbatim: late inference destroys predictability; named downstream consumers (Inc 5/7) |
| Users | 3 | Three personas with concrete pains, consistent with the merged Increments 1–2 |
| Goals | 3 | §9.2 schema and §9.5 acceptance rules translate 1:1 into MoSCoW rows |
| Success | 3 | Numbered: ≥12 rule tests, ≥2 legacy tests, ≥3 documental anchors, 0 regressions |
| Scope | 3 | Each deferral mapped to its owning increment (4, 5, 6, 7) |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. One *how* decision deferred to Design: whether `TM.*` graph rules live in a `DesignPhaseContract` that also carries the section rules, or compose the existing `SddPhaseContract` internally — Design picks from the engine structure, honoring the byte-identical-presence constraint.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial version — extracted from the incremental-improvements plan §9/§18 (PR 3 scope) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_TASK_MANIFEST.md`
