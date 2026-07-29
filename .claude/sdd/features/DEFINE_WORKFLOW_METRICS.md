# DEFINE: Workflow Metrics

> A versioned, machine-readable `workflow_metrics` block emitted by Build and summarized by Ship — measured values or `null` with a reason, never estimates — so two runs can be compared on rigor, cost, and defects without reading prose. No adaptive automation.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | WORKFLOW_METRICS |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 15/15 |

**Source:** plan §15 (metrics catalog §15.1, schema §15.2, usage §15.3, acceptance §15.4), §16.1/§16.2 test layers, §18 PR 9 ("no premature adaptive automation"). Phase 0 carried by the ratified plan. Consumes: fix rounds + verdicts (Inc 1/5), risk overrides (Inc 2), task manifest + parallelism (Inc 3/7), TDD evidence (Inc 4), findings by stage (Inc 5), coverage matrix (Inc 6), operational skips (run ledger).

---

## Problem Statement

The program produces rich evidence (matrices, verdicts, fix rounds, gate ledgers) but no comparable numbers (§5 "Métricas | Inexistente"): answering "did rigor go up and defects go down between run A and run B?" today means reading two BUILD_REPORTs and two run ledgers end to end. §15.4 sets the bar — two executions must be comparable without analyzing prose — and §15.2 forbids the failure mode that makes naive metrics worse than none: fabricated values (unavailable data must be `null` with a `reason`, never estimated).

---

## Target Users

| ID | User | Role | Pain Point |
|----|------|------|------------|
| - | AgentSpec maintainer (Matheus) | Compares runs across increments/benchmarks | No machine-readable surface; comparisons are manual prose archaeology |
| - | Autopilot runs | Emit evidence per phase | Durations, retries, and skips exist in the ledger but in table prose, not parseable data |
| - | Benchmark repetition (§22) | Needs rigor/cost/defect deltas | Without versioned metrics, the §22 targets (tests ≥95, time ≤1.5× baseline) cannot be verified mechanically |

---

## Goals

What success looks like (prioritized):

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | **MUST** | `workflow_metrics` contract block in `WORKFLOW_CONTRACTS.yaml` (schema_version 1): the §15.1 catalog as named keys — phase/task durations, time to first GREEN, task count, effective parallelism, tests by type, reopened tasks, local + final fix rounds, findings by severity and stage, requirements covered/excepted, operational skips, risk overrides, tokens/cost — with the availability rule (`null` + `reason`, never estimated; tokens/cost only when the platform provides them reliably) and per-consumer `behavior:` (build emits + validates, ship summarizes) |
| REQ-002 | **MUST** | `BUILD_REPORT_TEMPLATE.md` gains a **Workflow Metrics** section holding one fenced `yaml` `workflow_metrics:` block (schema §15.2 shape: `schema_version`, `feature`, then the catalog keys) |
| REQ-003 | **MUST** | `sdd-build` SKILL: emit the block from measured values only — a value the build did not measure is `null` with a `reason`; estimating, interpolating, or copying a prior run's numbers is forbidden conduct |
| REQ-004 | **MUST** | `sdd-ship` SKILL: Ship summarizes the block into SHIPPED (metrics table + lessons) and validates its presence/shape via the build contract; explicit boundary — metrics NEVER auto-change policies; risk recalibration requires multiple comparable runs AND human review (§15.3) |
| REQ-005 | **MUST** | Linter enforcement (BuildReportContract, opt-in like BR.*): block present + parseable when configured, `schema_version` matches the contract, every `null` carries a `reason`, no estimate markers (`~`, `approx`, `estimated`) in metric values; legacy reports without the block keep the legacy-mode path (WARN in `warn`, FAIL in `fail`) |
| REQ-006 | **MUST** | Version bump (v3.16.0) + history entry |
| REQ-007 | **SHOULD** | Tests: unit (§16.1 "avaliação" layer — valid block passes, null-without-reason fails, schema mismatch fails, estimate markers fail, legacy path) + documental anchors (template section, build measure-don't-estimate conduct, ship summary + no-adaptive-automation boundary) |
| REQ-008 | **COULD** | Comparability note: two blocks with the same schema_version diff key-by-key; a `compare two runs` example in the contract comments |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] Contract block: schema_version 1 + ≥12 catalog keys, each named; availability rule verbatim (`null` + `reason`, never estimated) — ≥2 documental tests
- [ ] Linter: ≥4 new BR.metrics rules, ≥6 unit tests (valid / null-no-reason / schema mismatch / estimate marker / absent-legacy warn / absent-configured fail)
- [ ] Conduct anchored: build measure-don't-estimate, ship summary + no-adaptive-automation boundary — ≥3 documental tests
- [ ] Both suites green; build + Step 5e parity exit 0; prior anchors intact; TDD evidence for the linter rules (RED before GREEN, per Inc 4 policy at medium risk)

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Contract registered | contracts YAML | documental test | schema_version 1 + §15.1 catalog keys + availability rule + behavior per consumer |
| AT-002 | Template shape | BUILD_REPORT_TEMPLATE.md | documental test | Workflow Metrics section with fenced yaml `workflow_metrics:` block |
| AT-003 | Valid block passes | report with measured values + nulls-with-reason | spec-lint --phase build | exit 0, no metrics findings |
| AT-004 | Fabrication rejected | `null` without `reason`; value with estimate marker | spec-lint --phase build | FAIL naming the key |
| AT-005 | Schema versioned | block with schema_version ≠ contract | spec-lint --phase build | FAIL (version mismatch named) |
| AT-006 | Legacy path | report without the block | legacy-mode warn / fail | WARN / FAIL respectively; pre-Inc-9 archives unaffected (not linted) |
| AT-007 | Build conduct | sdd-build SKILL | documental test | Measured-only rule; null+reason; estimation forbidden |
| AT-008 | Ship conduct | sdd-ship SKILL | documental test | Summary into SHIPPED; no-adaptive-automation boundary verbatim |
| AT-009 | Comparability | two valid blocks | unit test | Same schema_version → key-by-key comparison with no prose parsing |
| AT-010 | Parity + prior anchors | build + suites | Run | Exit 0; all prior increments' tests green |

---

## Out of Scope

- Adaptive automation of any kind — no automatic risk recalibration, no policy changes driven by metrics (§15.3, §18 PR 9); requires multiple comparable runs + human review, a future program
- Token/cost estimation — recorded only when the platform provides them reliably, else `null` + reason (§15.1)
- Telemetry upload, dashboards, or external storage (local artifact only; "Add telemetry" stays a separate CLAUDE.md task)
- The §22 benchmark repetition itself (this increment builds the measuring stick, not the experiment)
- Rewriting the run ledger format (metrics complement it; the ledger stays the run's source of state)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; Step 5e parity | Repackage before ship |
| Technical | Block lives inside BUILD_REPORT (single-artifact story, like the task manifest in DESIGN) | Linter parses the fenced yaml exactly like TM parses the manifest |
| Compatibility | Opt-in contract block + legacy-mode path; archived pre-Inc-9 reports untouched | No retro-editing of archives |
| Process | Dogfooding under `/auto`: this run's own BUILD_REPORT carries the first real block — with honest `null`s where the run didn't measure | Live validation incl. the availability rule |
| Process | Inc 4 policy at medium risk: linter rules are logic-bearing → TDD mode on for those tasks (RED-GREEN evidence in the report) | First TDD-mode increment of the program |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `WORKFLOW_CONTRACTS.yaml`, `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`, `.claude/skills/{sdd-build,sdd-ship}/SKILL.md`, `tools/spec-linter/spec_linter/contracts/build_report.py`, `tools/spec-linter/tests/`, `tests/` | Contract data + template + conduct + linter code |
| **KB Domains** | `python`, `testing`, `pydantic` | YAML parsing + rule tests |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

The `workflow_metrics` block IS the data contract: schema_version 1, §15.2 shape, availability rule. Consumers: linter (validation), ship (summary), future benchmark comparisons (diff).

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: medium
  reasons:
    - "blast_radius medium: linter code change + a template section every future build emits"
    - "no elevation floor: additive opt-in block; no external action, no data movement"
  dimensions:
    data_loss: none
    security: none
    reversibility: low
    blast_radius: medium
    migration: low
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
| A-001 | The fenced-yaml-in-markdown parsing used by the task manifest (Inc 3) transfers to a block inside BUILD_REPORT | New extraction helper in build_report.py — small, same pattern | [ ] |
| A-002 | The §15.1 catalog maps to ≥12 stable keys without inventing sensors — values the run can't measure are honest `null`s | Catalog shrinks to what's measurable; the availability rule absorbs the rest | [ ] |
| A-003 | Ship-side validation rides the existing build contract gate (ship refuses an incomplete report) — no separate ship linter phase needed | Add a ship-phase check — out of MVP unless Design finds a gap | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §5 gap + §15.4 comparability bar + fabrication failure mode, verbatim |
| Users | 3 | Maintainer/autopilot/benchmark pains concrete |
| Goals | 3 | §15.1–15.4 map 1:1 to REQ IDs; availability rule and no-automation boundary explicit |
| Success | 3 | Numbered floors incl. TDD evidence requirement |
| Scope | 3 | Adaptive automation, telemetry, token estimation, benchmark run — all excluded by name |
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
| 1.0 | 2026-07-29 | define-agent | Initial — plan §15/§16/§18 (PR 9) under the /auto pre-ignition interview |
