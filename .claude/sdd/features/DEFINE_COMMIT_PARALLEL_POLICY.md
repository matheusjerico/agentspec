# DEFINE: Commit Parallel Policy

> Make commits and parallel dispatch contractual conduct: per-task Conventional Commits linked in the report (SHA or `unavailable`), commit hygiene rules as data, and parallel dispatch of validated `parallel_group` tasks under explicit preconditions — conflicts serialize, never auto-merge.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | COMMIT_PARALLEL_POLICY |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 15/15 |

**Source:** plan §13 (commits §13.1, parallelism §13.2, acceptance §13.3), §18 PR 7 ("after the task graph is stable" — it is: Increments 3/5/6 shipped ids, write-sets, reviews, coverage). Phase 0 carried by the ratified plan. Mostly conduct + contract data; the graph-integrity sensors this policy relies on already exist (TM.write_conflict, TM.cycle).

---

## Target Users

| ID | User | Role | Pain Point |
|----|------|------|------------|
| - | AgentSpec maintainer (Matheus) | Reviews PRs task by task | Commits mix unrelated tasks; no deterministic task→commit linkage |
| - | Autopilot runs | Build dispatches manifest tasks | `parallel_group` is declared-but-dormant since Increment 3; no sanctioned dispatch policy |
| - | Plugin consumers | Run builds outside Git or in fresh repos | No fallback semantics — commit steps fail or get skipped silently |

---

## Problem Statement

Commit practice is informal (§5 "Commits atômicos | Informal") and parallel dispatch is unsanctioned: manifest tasks declare `parallel_group` and conventional-commit intents since Increment 3, but Build serializes everything, commits are ad-hoc session-level checkpoints mixing tasks, nothing links a commit to the task and verifications that produced it (§13.3), and a Git-less environment has no defined behavior.

---

## Goals

What success looks like (prioritized):

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | **MUST** | `commit_parallel` contract block: commit rules as data (§13.1 — per-task Conventional Commit from `execution.commit`; never mix independent tasks; never commit failing tests except a sanctioned RED commit; never rewrite history without authorization; squash/rebase is the maintainer's decision), Git-less fallback (`commit: unavailable`), and the parallel preconditions (§13.2 — dependencies complete, disjoint write-sets, no shared migration/contract in dispute, agent budget allows, merge strategy defined; conflicts serialize, never auto-merge) |
| REQ-002 | **MUST** | `sdd-build` SKILL: per-task commit conduct — after a task's verification (and its Step 4.6 review), commit that task's files with its manifest `execution.commit` message; record the SHA in the report; no Git → `unavailable`, never a blocker |
| REQ-003 | **MUST** | `sdd-build` SKILL: parallel dispatch policy — same-`parallel_group` tasks whose dependencies are complete MAY be dispatched concurrently (background Task tool) because their write-sets were validated disjoint at Design (TM.write_conflict); any runtime conflict or precondition failure serializes — never an automatic risky merge |
| REQ-004 | **MUST** | `BUILD_REPORT_TEMPLATE.md` Task Execution table gains a `Commit` column (SHA short / `unavailable` / `session` for tasks folded into a session checkpoint with justification) |
| REQ-005 | **MUST** | `sdd-autopilot` note: under `/auto`, per-task commits compose with checkpoint commits (task commits during Build; phase checkpoints unchanged); parallel dispatch respects the run's agent budget |
| REQ-006 | **MUST** | Version bump + history |
| REQ-007 | **SHOULD** | Documental tests: block shape, skill conduct anchors, template column, autopilot note |
| REQ-008 | **COULD** | RED-commit grammar note in the TDD section (a failing-test commit is sanctioned only when explicitly marked) |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] `commit_parallel` block: 5 commit rules + 5 parallel preconditions + fallback semantics as data, asserted verbatim by ≥3 documental tests
- [ ] sdd-build conduct anchors (per-task commit, SHA linkage, unavailable fallback, dispatch preconditions, serialize-on-conflict) — ≥4 documental tests
- [ ] Template Commit column + autopilot composition note — ≥2 documental tests
- [ ] 0 new linter rules (explicit scope boundary); both suites green; build + Step 5e parity exit 0
- [ ] 0 regressions in existing documental suites (task manifest/review/matrix anchors untouched)

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Block registered | contracts YAML | documental test | 5 commit rules + 5 preconditions + fallback present verbatim |
| AT-002 | Per-task commit conduct | sdd-build SKILL | documental test | Commit step after review; SHA recorded; message from execution.commit |
| AT-003 | Git-less fallback | sdd-build SKILL | documental test | `commit: unavailable` never blocks |
| AT-004 | Dispatch preconditions | sdd-build SKILL | documental test | All 5 preconditions + serialize-on-conflict anchored |
| AT-005 | Template column | BUILD_REPORT template | documental test | Commit column with sha/unavailable/session vocabulary |
| AT-006 | Autopilot composition | sdd-autopilot SKILL | documental test | Task commits + checkpoint commits coexist; budget respected |
| AT-007 | History entry | version_history | documental test | COMMIT_PARALLEL_POLICY (Increment 7) recorded |
| AT-008 | No linter change | spec_linter sources | suite run | Existing 172 linter tests pass unchanged; no new rule ids introduced |
| AT-009 | Existing anchors intact | prior documental suites | suite run | All prior increments' tests green |
| AT-010 | Parity | build | Step 5e | Exit 0 |

---

## Out of Scope

- New linter rules (explicit §18 PR 7 boundary — the graph sensors that make parallelism safe already exist at Design time)
- Enforcing commit linkage in the report contract (a future increment may add a BR rule once adoption exists; this increment establishes the conduct and column)
- Automatic merge/rebase of parallel work (conflicts serialize by policy)
- Changing checkpoint-commit semantics in the autopilot lifecycle
- Increments 8–9

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; Step 5e parity | Repackage before ship |
| Technical | Parallel dispatch trusts Design-time TM.write_conflict validation; runtime conflicts serialize | No new sensors needed |
| Compatibility | v1 builds (no manifest) keep session-level commits — `session` vocabulary covers them | No forced granularity |
| Process | Dogfooding under `/auto`: this run itself uses per-task-derived commits where practical and records the Commit column | Live shape validation |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `WORKFLOW_CONTRACTS.yaml`, `.claude/skills/{sdd-build,sdd-autopilot}/SKILL.md`, `BUILD_REPORT_TEMPLATE.md`, `tests/` | Conduct + data increment |
| **KB Domains** | `python`, `testing` | Documental tests only |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

Not applicable — framework feature.

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: low
  reasons:
    - "conduct + contract data + one template column; zero linter/code changes"
    - "reversibility low, blast_radius low: no gate semantics change"
  dimensions:
    data_loss: none
    security: none
    reversibility: low
    blast_radius: low
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
| A-001 | Per-task commits inside an autopilot run compose cleanly with phase checkpoint commits (task commits become part of the branch history the checkpoint summarizes) | Would need checkpoint semantics change — explicitly out of scope; fall back to session commits with `session` vocabulary | [ ] |
| A-002 | Design-time write-conflict validation is sufficient safety for concurrent dispatch (runtime file collisions outside declared write-sets are a conduct violation, serialized on detection) | Would need runtime locking — rejected as scope creep; serialize-on-conflict covers it | [ ] |
| A-003 | The Commit column is additive to the report parsers (Task Execution rows already tolerate extra columns — cell-count guards are minimums) | Parser tweak — small | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §5 informal-commits gap + dormant parallel_group, verbatim |
| Users | 3 | Reviewer, autopilot, Git-less consumers — each with the concrete pain |
| Goals | 3 | §13.1/13.2 rules map 1:1 with REQ IDs (new column dogfooded) |
| Success | 3 | Numbered documental floors; explicit zero-linter-rule boundary |
| Scope | 3 | Enforcement deferral, merge automation exclusion, checkpoint invariance all named |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial — plan §13/§18 (PR 7) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_COMMIT_PARALLEL_POLICY.md`
