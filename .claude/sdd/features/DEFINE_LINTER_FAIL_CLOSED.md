# DEFINE: Linter Fail Closed

> Close the three fail-open paths the Codex cross-model review found in the spec-linter: configuration that is present-but-invalid must be an operational error (never a silent disarm), and malformed matrix/task-review rows must be FAIL findings (never silent drops that hide a MUST or a dirty verdict).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | LINTER_FAIL_CLOSED |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 15/15 |

**Source:** `docs/reviews/2026-07-29-codex-review-prs-5-13.md` (Codex adversarial review of PRs #5–#13 — findings 1–3, per-finding change maps, execution order). Phase 0 carried by the ratified review document. Hardens: Increments 2/4/5/6/9 wiring and parsers.

---

## Problem Statement

Three verified fail-open paths survive the nine-increment program, all one class: **silent drop / silent fallback where fail-closed is required**. (1) The CLI arms the four opt-in rule families only when their top-level block `isinstance dict` — a block present but malformed (null, string, list, indentation drift) silently disarms TDD enforcement, task review, MUST coverage, or metrics, with zero signal. (2) A truncated (<8-cell) or placeholder-bearing Traceability Matrix row is dropped without a finding — `matrix_present` stays true, `BR.matrix_missing` stays quiet, and the dropped MUST never reaches `BR.must_uncovered`: a high-risk report can hide exactly the uncovered MUST row and PASS. The design-side parser (<6 cells) has the identical hole. (3) A Task Reviews row with <5 cells or placeholders is ignored; at low risk `BR.task_review_missing` is silent by policy, so a `dirty` verdict hidden by truncation escapes `BR.task_review_dirty` entirely. The code's own "disclosed residual" comments mark all three spots.

---

## Target Users

| ID | User | Role | Pain Point |
|----|------|------|------------|
| - | AgentSpec maintainer (Matheus) | Trusts gate verdicts | A PASS can currently mean "the control was silently off" or "the bad row was silently dropped" |
| - | Autopilot runs | Gates decide proceed/abort | Gate L consumes verdicts that malformed input can hollow out |
| - | Plugin consumers | Copy contracts YAML into their repos | An indentation typo in their contracts file disarms enforcement without any error |

---

## Goals

What success looks like (prioritized):

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | **MUST** | `cli.py` `_build_report_contract`: for each of `tdd_policy`, `task_review`, `traceability`, `workflow_metrics` — key **absent** keeps rules dormant (compatibility unchanged); key **present with a non-mapping value** (null, string, list, int) raises `_OperationalError` (exit 2) naming the block and the found type. `traceability` additionally validates `verification_types` is a list of strings before arming `matrix_must_coverage` |
| REQ-002 | **MUST** | Same discipline on the design side: `_design_phase_contract` and the phase-routing gate — `task_manifest`/`traceability` present-but-non-mapping → exit 2, never a silent disarm and never a silent downgrade to the plain section-only contract |
| REQ-003 | **MUST** | Build matrix parser: every numbered row of the filled `## Traceability Matrix` with <8 cells, or a `{placeholder}` in the REQ/Priority cells, becomes a `BR.matrix_row_malformed` FAIL naming the row — at every risk level; the silent-drop guard and its "disclosed residual" comment are removed |
| REQ-004 | **MUST** | Design matrix parser: same rule as `TX.matrix_row_malformed` FAIL for rows with <6 cells or placeholder REQ/Priority |
| REQ-005 | **MUST** | Task Reviews parser: rows with <5 cells or placeholder task-id/verdict become `BR.task_review_row_malformed` FAIL — independent of the risk-level severity gate that scopes `task_review_missing`; residual comment removed |
| REQ-006 | **MUST** | Version bump v3.17.0 + history entry describing the fail-closed hardening; plugin rebuilt, parity green |
| REQ-007 | **SHOULD** | Tests, TDD RED-first for all rule/wiring changes: parametrized CLI cases (4 build blocks + 2 design blocks × null/string/list → exit 2; absent → dormant green), malformed-row regressions (1–7 cell MUST rows build-side, 1–5 design-side, short row containing `dirty`, placeholder verdict, placeholder REQ), prior suites intact |
| REQ-008 | **COULD** | `tools/spec-linter/USAGE.md` note: configuration is fail-closed — present-but-invalid blocks are exit-2 errors, not silent disables |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] 3 new FAIL rules (`BR.matrix_row_malformed`, `TX.matrix_row_malformed`, `BR.task_review_row_malformed`) — ≥9 unit tests covering the truncation/placeholder grid
- [ ] 6 wiring paths fail-closed (4 build blocks + 2 design blocks) — ≥12 parametrized CLI tests (present-invalid → exit 2; absent → dormant)
- [ ] 0 remaining "dropped without a diagnostic" residual comments on the three fixed paths
- [ ] Both suites green (root ≥172, spec-linter ≥193 before additions); build + parity exit 0; RED evidence recorded before each GREEN

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Config null | `tdd_policy:` (null) in contracts | spec-lint --phase build | exit 2 naming tdd_policy |
| AT-002 | Config string/list | `task_review: "yes"` / `traceability: []` / `workflow_metrics: 1` | spec-lint --phase build | exit 2 naming the block and type |
| AT-003 | Config absent | block removed entirely | spec-lint --phase build | rules dormant, prior behavior (green fixture passes) |
| AT-004 | Design config invalid | `task_manifest: "x"` or `traceability: null` | spec-lint --phase design | exit 2 — never silent downgrade to the plain contract |
| AT-005 | Truncated MUST row (build) | matrix row with 1–7 cells | lint | BR.matrix_row_malformed FAIL naming the row; must_uncovered unaffected for intact rows |
| AT-006 | Placeholder row (build) | `{REQ}` or `{Priority}` cell | lint | BR.matrix_row_malformed FAIL |
| AT-007 | Truncated row (design) | matrix row with 1–5 cells or placeholder | lint | TX.matrix_row_malformed FAIL |
| AT-008 | Hidden dirty review | 4-cell Task Reviews row containing `dirty`; placeholder verdict row — at risk low | lint | BR.task_review_row_malformed FAIL (severity gate does not apply) |
| AT-009 | Intact artifacts unaffected | current valid fixtures + this repo's own archived reports shape | full suites | all prior tests green, no new findings on well-formed rows |
| AT-010 | Parity + history | build + version_history | run + documental test | exit 0; v3.17.0 entry present |

---

## Out of Scope

- New contract blocks or catalog changes (hardening only — no new configuration surface)
- Retro-linting archived pre-existing reports (archives stay unlinted)
- The template files themselves (placeholder rows in templates are authoring surfaces, not linted artifacts)
- `pr_readiness`, `commit_parallel`, `risk_profiles` blocks (conduct data — no linter wiring to harden)
- Estimate-marker or availability-rule changes (Increment 9 scope, already shipped)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; plugin parity via build | Repackage before ship |
| Compatibility | Absent blocks keep today's dormant behavior byte-for-byte; only present-invalid input changes outcome (silent → exit 2) and malformed rows (silent → FAIL) | Well-formed repos see zero change |
| Process | TDD required (medium risk, logic-bearing linter code — Inc 4 policy); RED before GREEN per rule | Evidence in the report |
| Process | Single hardening PR; /auto terminal state is the open PR (merge is a separate human decision — the 9-increment program's standing merge authorization ended with PR #13) | PR opened, not merged |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/spec_linter/{cli.py, contracts/build_report.py, contracts/design_phase.py}`, `tools/spec-linter/tests/`, `WORKFLOW_CONTRACTS.yaml` (version+history only), `tools/spec-linter/USAGE.md` | Linter code + tests + version data |
| **KB Domains** | `python`, `testing` | Parser + CLI validation patterns |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

No schema changes — the contracts YAML vocabulary is unchanged; only the CLI's tolerance for malformed instances of it tightens (absent = dormant; present-invalid = exit 2).

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: medium
  reasons:
    - "blast_radius medium: every lint invocation crosses the hardened wiring; three parsers gain FAIL rules"
    - "reversibility low: pure code change, revert restores prior tolerance"
  dimensions:
    data_loss: none
    security: low
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
| A-001 | No existing valid fixture or this repo's own artifacts rely on the silent-drop behavior (all well-formed rows have full cardinality) | Fixtures adjusted to full shape — the rules are the point | [ ] |
| A-002 | Present-but-null (`key:` with no value) is distinguishable from absent via `key in data` (yaml maps null) | Fall back to treating explicit null as invalid only when detectable | [ ] |
| A-003 | The design-phase routing gate can raise exit 2 for invalid blocks without disturbing the both-absent → plain-contract path | Restructure routing slightly; same observable contract | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Three findings with file:line, mechanism, and the code's own residual comments as evidence |
| Users | 3 | Maintainer/autopilot/plugin-consumer failure modes concrete |
| Goals | 3 | Review doc's change map transposed 1:1 into REQ IDs with rule names |
| Success | 3 | Numbered floors: 3 rules, 6 wiring paths, test grids, zero residual comments |
| Scope | 3 | No new config surface, no retro-linting, conduct blocks excluded, merge decision excluded — all named |
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
| 1.0 | 2026-07-29 | define-agent | Initial — Codex review doc ratified as Phase 0 under the /auto pre-ignition interview |
