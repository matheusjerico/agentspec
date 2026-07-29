# DEFINE: Build Report Contract Enforcement

> Make the Build Quality Gates guarantees executable: a `build` phase contract in WORKFLOW_CONTRACTS.yaml, spec-linter semantic rules for the Build Report, a wired pre-handoff gate in Build and Ship, and plugin parity proof.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_REPORT_CONTRACT_ENFORCEMENT |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

**Source:** `docs/superpowers/plans/2026-07-29-agentspec-incremental-improvements.md` — Increment 1 (§7) / PR 1 (§18). This is the foundation increment: Increments 2–9 build on the evidence discipline established here.

---

## Problem Statement

The Build Quality Gates baseline (Review Verdict, Gate R, TDD Evidence — shipped 2026-07-29 as BUILD_QUALITY_GATES) is functional, but its guarantees rest on textual consistency between Markdown skills, YAML contracts, and templates: the Build phase binding in `WORKFLOW_CONTRACTS.yaml` is declared `specified target`, not `wired`, so a malformed, incomplete, or dishonest BUILD_REPORT can still reach Ship without any deterministic check catching it.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer | Develops the framework, plans Increments 2–9 | Cannot layer new rigor (risk profiles, task manifest, TDD policy) on gates that are only documentary promises |
| Autopilot runs (`/auto`, `autopilot.sh`) | Autonomous SDD execution where gates, not humans, decide | Gate R decisions read Build Report fields that nothing validates — a fabricated `clean` verdict passes silently |
| Plugin consumers (vendored installs, user projects) | Run the distributed plugin built from `.claude/` | No proof that `plugin/` policies match the canonical source; drift ships invisibly |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | Declare a Build phase contract: `required_sections` for `BUILD_REPORT_{FEATURE}.md` in `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` |
| **MUST** | Flip the Build consumer binding from `specified target` to `wired (document-level)` |
| **MUST** | Extend spec-linter with Build semantic rules: (a) Review Verdict present with an allowed value; (b) no open Critical/Important finding; (c) `Fix rounds used` consistent with the 2-round budget; (d) TDD Evidence present when the TDD mode was mandatory for the run; (e) all tasks complete before `Overall: ✅ COMPLETE` |
| **MUST** | `sdd-build` runs the contract gate after writing the Build Report and before handoff — FAIL means Build does not declare completion |
| **MUST** | `sdd-ship` re-validates the same artifact against the same contract — the same reasons that fail Build refuse Ship |
| **MUST** | Legacy-report policy: manual runs get WARN plus migration guidance; Autopilot treats `missing`/FAIL as blocking; resuming an old run generates a compatibility section for review |
| **MUST** | Bump the `WORKFLOW_CONTRACTS.yaml` version and record the change history (per plan §17.1) |
| **SHOULD** | Parity test proving `.claude/` and `plugin/` agree after `build-plugin.sh` (modulo documented path rewrites) |
| **SHOULD** | Engine and gate-state tests (rule behavior on fixtures), not only documental substring tests |
| **COULD** | Calibration dry-run of the new rules against archived BUILD_REPORTs (BUILD_QUALITY_GATES, AUTOPILOT_IGNITION_GATE, …) |
| **COULD** | Update `tools/spec-linter/USAGE.md` / `README.md` for the new Build phase rules |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] A valid Build Report receives PASS (exit 0) from `spec-lint --phase build`; a report with verdict `dirty`, a `missing` verdict, or ≥1 open Critical/Important finding receives FAIL (exit 1)
- [ ] Each of the 5 semantic rule families has ≥1 PASS-path and ≥1 FAIL-path test (≥10 new rule tests total)
- [ ] Build refuses to declare completion and Ship refuses the artifact on contract FAIL — each demonstrated by ≥1 fixture-driven test
- [ ] Plugin parity: 0 undocumented diffs between canonical policy files and their `plugin/` equivalents after `build-plugin.sh`, enforced by 1 automated test
- [ ] 0 regressions: the existing repo suite (27 tests) and the spec-linter suite stay green
- [ ] Legacy behavior: a pre-contract report produces WARN (not FAIL) in manual mode, and blocks under Autopilot — each covered by ≥1 test

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Valid report passes | A Build Report with verdict `clean`, no open blocking findings, fix rounds ≤2, tasks complete | `spec-lint --phase build` runs | Exit 0, verdict PASS |
| AT-002 | Dirty verdict blocks | A report with Review Verdict `dirty` | Linter runs | Exit 1, FAIL naming the verdict rule |
| AT-003 | Missing verdict blocks | A report without the Review Verdict section | Linter runs | Exit 1, FAIL naming the missing section |
| AT-004 | Open blocking finding | A report with verdict `clean-with-minors` but 1 open Important finding | Linter runs | Exit 1, FAIL naming the open finding |
| AT-005 | Fix-round budget breach | A report recording `Fix rounds used: 3/2` | Linter runs | Exit 1, FAIL naming budget inconsistency |
| AT-006 | Missing TDD evidence | A run where TDD was mandatory, report lacks TDD Evidence | Linter runs | Exit 1, FAIL naming the TDD rule |
| AT-007 | Incomplete tasks vs. status | A report with an incomplete task and `Overall: ✅ COMPLETE` | Linter runs | Exit 1, FAIL naming the completeness rule |
| AT-008 | Legacy report, manual mode | A pre-contract Build Report (no verdict schema), manual run | Linter runs | WARN with migration guidance; phase proceeds visibly |
| AT-009 | Legacy report, Autopilot | The same pre-contract report | Autopilot Gate R evaluates it | Run blocks (fail-closed), gap recorded in the run report |
| AT-010 | Plugin parity | A policy file mutated only in `plugin/` | Parity test runs after `build-plugin.sh` | Test fails, naming the divergent file |

---

## Out of Scope

Explicitly NOT included in this feature:

- Increments 2–9 of the source plan: risk profiles, executable task manifest, risk-driven TDD, incremental Task Review, traceability/coverage matrix, commit & parallelism policy, PR Readiness gate, workflow metrics — each is its own future DEFINE
- Cross-model second opinion on the branch review (plan §5 "Revisão final") — Judge-layer work, not linter work
- Changes to spec-judge (behavioral enforcement) — this increment is deterministic linting only
- A new workflow phase or changes to the 5-phase structure (plan §21)
- Rewriting the Build Report template's shape beyond what the contract needs (additive fields only)
- Auto-migration tooling that rewrites legacy reports (guidance only in this increment)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` is canonical; `plugin/` is generated by `build-plugin.sh` — manual `plugin/`-only edits are prohibited (plan §4.3) | Parity must be proven by test, never assumed; all changes land in `.claude/` first |
| Technical | spec-linter stays deterministic — no model calls | Semantic rules are limited to parseable report fields; judgment-based checks stay in spec-judge |
| Technical | The exit-code contract (0/1/2) and verdict semantics are owned by the `contract_enforcement` block — consumers never reinterpret | New rules emit findings inside the existing verdict model; no new exit codes |
| Compatibility | `dirty`/`missing` verdicts are fail-closed from day one (plan §17.2); other new rules may enter via Observe/Warn before Enforce | Rollout mode is per-rule, and legacy artifacts stay readable (plan §4.6) |
| Process | Dogfooding (plan §16.4): this feature runs through the SDD workflow and its branch passes its own adversarial review | The feature's own Build Report becomes the first real artifact validated by the new contract |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/` (rules + tests), `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`, `.claude/skills/{sdd-build,sdd-ship,sdd-autopilot}/`, `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`, `tests/`, `build-plugin.sh` | Framework/tooling feature — no `src/` application code |
| **KB Domains** | `python`, `testing` | Linter rules are Python; test strategy leans on pytest fixture patterns |
| **IaC Impact** | None | Local tooling and documents only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

Not applicable — this is a framework/tooling feature with no data pipelines, ETL, or analytics surface.

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | The spec-linter rule engine can express cross-field semantic rules (allowed verdict values, fix-round consistency), not just section presence | Needs a rules-engine extension in `spec_linter/rules.py` first — Design must scope that extension explicitly | [ ] |
| A-002 | BUILD_REPORT template section names (Review Verdict, TDD Evidence, Final Status, …) are stable enough to bind a contract on | Template changes would cascade to contract + linter; contract should bind on stable section identifiers | [ ] |
| A-003 | Whether TDD was mandatory for a run is detectable from the report itself (metadata field or explicit marker) | The TDD-evidence rule cannot fire deterministically; Design must add a report metadata field | [ ] |
| A-004 | The 8 existing documental tests in `tests/test_build_quality_gates.py` remain valid; new tests are additive | Contract drift between old and new tests would need reconciliation before wiring | [ ] |
| A-005 | Plugin parity is testable by content comparison after `build-plugin.sh`, since path rewrites are deterministic | Parity would need a rewrite-aware normalizer, increasing scope of the SHOULD goal | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific and evidence-based: binding declared `specified target` at `WORKFLOW_CONTRACTS.yaml`; guarantee gap named in plan §7.1 |
| Users | 2 | Personas are real but inferred from repo context (maintainer, Autopilot, plugin consumers) — the source plan does not name them explicitly |
| Goals | 3 | Plan §7.2 enumerates the implementation directly; MoSCoW split is unambiguous |
| Success | 3 | Plan §7.4 acceptance criteria are directly testable; all criteria carry numbers |
| Scope | 3 | Increments 2–9 and plan §21 give explicit, itemized exclusions |
| **Total** | **14/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. Two decisions are explicitly deferred to the Design phase (they choose *how*, not *whether*):

1. **TDD-mandatory detection (A-003):** whether the report gains a metadata field (e.g., `TDD mode: required|opt-in|off`) or the linter infers it from an existing marker. Design picks the mechanism; the rule itself is a MUST either way.
2. **Rule placement:** whether Build semantic rules extend `spec_linter/rules.py` directly or land in a per-phase rules module. Design decides based on the current engine structure.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial version — extracted from `docs/superpowers/plans/2026-07-29-agentspec-incremental-improvements.md`, Increment 1 (§7) / PR 1 (§18, §23) |
| 1.1 | 2026-07-29 | ship-agent | Shipped and archived |

---

## Next Step

**Shipped** — cycle closed; see `SHIPPED_2026-07-29.md`
