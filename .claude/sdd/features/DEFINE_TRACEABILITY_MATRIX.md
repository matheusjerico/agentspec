# DEFINE: Traceability Matrix

> Every MUST/SHOULD requirement traceable to tasks, tests, and results: requirement IDs at Define, a matrix generated at Design and filled at Build, deterministic coverage validation for adopters, and the frontend/browser test policy.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TRACEABILITY_MATRIX |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 15/15 |

**Source:** plan §12 (model §12.1, coverage rules §12.2, verification types §12.3, frontend policy §12.4, acceptance §12.5), §18 PR 6, spine §6 (`requirement_id` must survive Define → PR). Consumes manifest `requirements` refs (Inc 3), Task IDs (Inc 3), review verdicts (Inc 5). Phase 0 carried by the ratified plan (§12.4 answers the benchmark's browser-blindspot defects directly).

---

## Problem Statement

Requirements lose their identity after Define (§5 "Falta propagação automática até tarefa, teste e PR"): goals have no stable IDs, no artifact links a MUST to the tasks that implement it or the tests that prove it, and coverage claims are prose — the benchmark's browser defects survived precisely because no matrix forced a behavioral test type onto UI requirements (§12.4).

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer (Matheus) | Owns program DoD "MUST rastreáveis até teste e PR" | No requirement_id exists; traceability is manual archaeology across four documents |
| Autopilot runs | Ship must confirm coverage from evidence | No deterministic sensor connects requirements to results — coverage is asserted, never checked |
| Plugin consumers | Ship features with web UIs | No policy forces e2e/browser/a11y/timezone coverage when a UI exists — the benchmark's exact defect class |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | `DEFINE_TEMPLATE.md` Goals table gains an `ID` column (`REQ-001`…); `sdd-define` assigns stable requirement IDs (spine §6: IDs survive Define → Design → Build → PR) |
| **MUST** | `DESIGN_TEMPLATE.md` gains a `Traceability Matrix` section — one row per MUST/SHOULD: `| REQ | Priority | Tasks | Tests | Verification Type |`; `sdd-design` generates it from the DEFINE goals + task manifest `requirements` refs |
| **MUST** | `BUILD_REPORT_TEMPLATE.md` gains the filled matrix — adds `Result` and `Review` columns; `sdd-build` fills them from verification runs and task-review verdicts |
| **MUST** | `traceability` contract block: verification-type vocabulary (§12.3: unit, integration, contract, e2e, browser_accessibility, security, migration_rollback, data_quality, observability, deterministic_inspection), coverage rules, enforcement map |
| **MUST** | `DesignPhaseContract` rules (adopters — matrix section present): `TX.must_without_task` (MUST row, empty Tasks → FAIL, §12.2), `TX.unknown_type` (type outside vocabulary → FAIL), `TX.orphan_reference` (matrix task ref not in the manifest, or manifest requirement ref not in the matrix → WARN) |
| **MUST** | `BuildReportContract` rules (adopters): `BR.must_uncovered` (MUST row with empty Tests or Result not Pass → FAIL, unless the row records a contractual exception), `BR.matrix_missing` (v2 + Risk-Level reports at high/critical without a matrix → WARN — adoption ramp; silent at/below medium) |
| **MUST** | Frontend/browser policy (§12.4) as `sdd-design` conduct + contract data: when the feature has a web UI — ≥1 e2e main-journey flow, loading/error/empty states, basic accessibility, timezone-relevant date behavior, URL/filter/state sync — each mapped to matrix rows with `e2e`/`browser_accessibility` types |
| **MUST** | Version bump + history |
| **SHOULD** | SHOULD-priority rows: deferral recorded explicitly (`deferred — <reason>` in Tests) is valid (§12.2); COULD rows omitted freely but removal recorded in the DEFINE revision |
| **COULD** | PR-description reuse guidance (matrix pasted, not reconstructed — full automation is Increment 8's PR-readiness surface) |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] `TX.must_without_task` FAIL (≥1), `TX.unknown_type` FAIL (≥1), `TX.orphan_reference` WARN both directions (≥2), valid matrix → 0 findings (≥1)
- [ ] `BR.must_uncovered`: empty Tests → FAIL (≥1), Result not Pass → FAIL (≥1), exception-recorded row → no finding (≥1); `BR.matrix_missing` WARN at high (≥1), silent at medium/low/legacy (≥2)
- [ ] Vocabulary (10 types) + coverage rules + frontend policy as contract data — ≥3 documental tests; template/skill anchors ≥5
- [ ] Absence is v1-silent at Design (no matrix → no TX findings) — ≥1 test; both suites green; build + Step 5e parity exit 0
- [ ] Requirement IDs: DEFINE template ID column + sdd-define step anchored — ≥2 tests

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Valid matrix at Design | DESIGN with matrix, MUSTs all tasked, known types | `spec-lint --phase design` | 0 TX findings |
| AT-002 | MUST without task | Matrix row `REQ-002 | MUST` with empty Tasks | Linter | Exit 1, `TX.must_without_task` |
| AT-003 | Unknown type | Row with type `vibes` | Linter | Exit 1, `TX.unknown_type` |
| AT-004 | Orphan refs | Matrix cites TASK-GHOST; manifest task cites REQ-GHOST | Linter | WARN both, exit 0 |
| AT-005 | No matrix at Design | DESIGN without the section | Linter | 0 TX findings (opt-in) |
| AT-006 | MUST uncovered at Build | Filled matrix, MUST row Tests empty | `spec-lint --phase build` | Exit 1, `BR.must_uncovered` |
| AT-007 | Result not Pass | MUST row Result `Fail` | Linter | Exit 1, same rule |
| AT-008 | Exception row | MUST row Tests `exception: contractual — <cite>` | Linter | No `BR.must_uncovered` finding |
| AT-009 | Matrix missing at high | v2 report, Risk Level high, no matrix | Linter | Exit 0, WARN `BR.matrix_missing`; medium/low/legacy silent |
| AT-010 | Anchors + parity | templates/skills/contracts + build | Documental tests + Step 5e | All pass; frontend policy items asserted |

---

## Out of Scope

- Full PR-description automation (Increment 8 consumes the matrix; here only guidance lands)
- Percentual line-coverage enforcement (§21 — matrix covers acceptance criteria, not line %)
- Executing tests or verifying test-to-behavior semantics (linter validates recorded structure; behavior is Build conduct + review)
- Retrofitting archived documents; forcing matrices on v1 designs
- Increments 7–9

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; Step 5e parity | Repackage before ship |
| Technical | Deterministic linter — structural matrix validation only | Behavior linkage is conduct + review |
| Compatibility | Matrix is opt-in at Design (like the manifest); Build-side `matrix_missing` is WARN-only and only at high/critical (adoption ramp §17.2) | No new FAIL on non-adopters |
| Compatibility | MUST-coverage FAILs only for adopters (matrix present) — mirrors manifest precedent | v1/legacy untouched |
| Process | Dogfooding under `/auto`: this feature's own DEFINE carries REQ IDs, its DESIGN a matrix, its report the filled matrix | The artifacts exercise their own rules |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/` (design_phase.py, build_report.py, cli, tests), `WORKFLOW_CONTRACTS.yaml`, templates (DEFINE/DESIGN/BUILD_REPORT), skills (sdd-define/sdd-design/sdd-build), `tests/` | Framework/tooling |
| **KB Domains** | `python`, `testing` | Established pattern |
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
  level: medium
  reasons:
    - "blast_radius medium: touches both phase contracts and three templates/skills"
    - "no elevation floor; new FAILs scoped to matrix adopters"
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
| A-001 | Matrix tables parse with the existing numbered-row + `_section_exact` machinery (Increment 5's lesson applied from birth) | Small parser addition | [ ] |
| A-002 | REQ-ID grammar `REQ-\d+` (plus legacy `MUST-n`/`SC-n` refs tolerated in manifests) suffices for matching | Extend the token grammar — additive | [ ] |
| A-003 | Design-side and build-side matrices can share one column-prefix shape (build adds Result/Review columns at the end) | Two shapes; parser branches on column count — already handled by cell-count guards | [ ] |
| A-004 | Frontend policy is conduct + data + anchors (no deterministic web-UI detector exists) | Accepted — same boundary as blind-first/RED-validity | [ ] |
| A-005 | `BR.matrix_missing` as WARN (not FAIL) at high/critical is the right adoption ramp for a NEW artifact this increment introduces | Severity bump later is one contract change | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §5 propagation gap + §12.4 benchmark defect class, verbatim |
| Users | 3 | Personas tied to DoD, sensors, and the browser blindspot |
| Goals | 3 | §12.1–12.4 map 1:1; every rule named with severity and phase |
| Success | 3 | Numbered per-rule floors; opt-in silences pinned |
| Scope | 3 | PR automation → Inc 8; line % excluded per §21; conduct/sensor boundary explicit |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. Deferred *how*: exact matrix column shapes and the REQ-token grammar (A-002/A-003).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial — plan §12/§18 (PR 6) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_TRACEABILITY_MATRIX.md`
