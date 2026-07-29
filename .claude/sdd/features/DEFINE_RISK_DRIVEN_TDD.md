# DEFINE: Risk Driven TDD

> Make TDD a verifiable policy instead of an opt-in flag: effective mode derived from risk level, task declarations, and flags; high/critical can never skip TDD silently; exceptions are categorized and linter-validated.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_DRIVEN_TDD |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 15/15 |

**Source:** `docs/superpowers/plans/2026-07-29-agentspec-incremental-improvements.md` — Increment 4 (§10), PR 4 scope §18 ("activates TDD-by-policy"), dependency §19 (consumes Increment 2's `risk_profile.level` and Increment 3's `execution.tdd`). Phase 0 carried by the ratified plan.

---

## Problem Statement

TDD is opt-in (`--tdd`) and its evidence only loosely validated (§10.1): a high-risk change can run without TDD and nothing blocks it, RED evidence is not checked for validity (§10.2 — a broken RED command or pre-existing failure counts as nothing), and there is no sanctioned exception path — so authors either fake evidence or skip silently (§5 "TDD | Parcial").

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer (Matheus) | Owns the §8.3 rigor matrix activation | The TDD row of the matrix exists as a table in a plan, not as enforceable policy |
| Autopilot runs (`/auto`, `autopilot.sh`) | Build must decide TDD mode without a human | No deterministic rule combines flag, risk level, and task declarations into one effective mode |
| Plugin consumers (vendored installs, user projects) | Ship risky changes through the workflow | High-risk work gets no TDD floor; doc-only tasks have no honest exception path (`n/a` is a free-text hole) |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | `tdd_policy` contract block in `WORKFLOW_CONTRACTS.yaml`: effective-mode rule as data — `effective TDD = strongest of (--tdd flag, risk_policy[risk level], any task execution.tdd: required)` (§10.1); `risk_policy`: low → recommended, medium → required_for_logic, high → required, critical → required (§8.3 TDD row) |
| **MUST** | `sdd-build` SKILL derives and records the effective mode: `TDD Mode: required` when risk level is high/critical or any manifest task declares `execution.tdd: required`; `opt-in` when only the flag; `off` otherwise — with the §10.2 cycle and RED-validity rules (a broken RED command, an unrelated import error, or a pre-existing failure is NOT evidence) |
| **MUST** | `--no-tdd` flag on `/build`: dispenses TDD only at low/medium risk WITH a recorded justification in the report; at high/critical it is refused and recorded (never silently honored) (§10.1) |
| **MUST** | `tdd_exception` path (§10.3): a TDD Evidence row may record `exception: <category> — <alternative verification>`; allowed categories live as contract data (e.g. non_executable_documentation, declarative_configuration, generated_artifact); empty or unknown categories FAIL the linter |
| **MUST** | `BuildReportContract` extensions: `BR.tdd_required_by_risk` — schema-v2 report with `Risk Level` high/critical and `TDD Mode: off` → FAIL; medium + off → WARN (required_for_logic is judgment-scoped); `BR.tdd_exception_invalid` — exception rows with unknown/empty category → FAIL; reports without a Risk Level row (pre-Increment-2) keep today's behavior (adoption warning path, §10.4) |
| **MUST** | Version bump + history (§17.1) |
| **SHOULD** | `/build` command doc: `--no-tdd` flag surface + constraint table |
| **SHOULD** | BUILD_REPORT template: TDD Evidence section documents the exception row format and the new-test/regression/alternative distinction (§10.4) |
| **COULD** | Ledger note in sdd-autopilot that Gate L (report, fail-mode) now transports the TDD policy rules — no gate change |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] `BR.tdd_required_by_risk`: high/critical + off → FAIL and medium + off → WARN, each with ≥1 test; low + off → 0 findings, ≥1 test
- [ ] `BR.tdd_exception_invalid`: unknown category → FAIL, known category → 0 findings, ≥2 tests
- [ ] Legacy: report without a Risk Level row → neither new rule fires, ≥1 test; pre-contract (no Schema Version) reports unchanged, existing tests stay green
- [ ] Effective-mode rule and risk_policy exist as contract data, asserted verbatim by ≥2 documental tests; skill/command anchors (`--no-tdd`, RED-validity, exception format) by ≥4
- [ ] 0 regressions: both suites green; `./build-plugin.sh` + Step 5e parity exit 0

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | High risk cannot skip TDD | v2 report, `Risk Level: high`, `TDD Mode: off` | `spec-lint --phase build` | Exit 1, `BR.tdd_required_by_risk` |
| AT-002 | Critical same | `Risk Level: critical (…)`, `TDD Mode: off` | Linter | Exit 1, same rule |
| AT-003 | Medium warns | `Risk Level: medium`, `TDD Mode: off` | Linter | Exit 0, WARN `BR.tdd_required_by_risk` |
| AT-004 | Low is silent | `Risk Level: low`, `TDD Mode: off` | Linter | 0 TDD-policy findings |
| AT-005 | Required + evidence passes | `Risk Level: high`, `TDD Mode: required`, TDD Evidence rows present | Linter | Exit 0 |
| AT-006 | Unknown exception category | Evidence row `exception: vibes — trust me` | Linter | Exit 1, `BR.tdd_exception_invalid` |
| AT-007 | Known exception category | Evidence row `exception: non_executable_documentation — markdownlint docs/` | Linter | 0 exception findings |
| AT-008 | Legacy (no Risk Level row) | v2 report without the row | Linter | Neither new rule fires |
| AT-009 | Policy as data + skill anchors | contracts/skill/command files | Documental tests | effective-mode rule, risk_policy, `--no-tdd` constraints, RED-validity anchors pass |
| AT-010 | Parity + suites | build + suites | Run | Exit 0, all green |

---

## Out of Scope

Explicitly NOT included (plan §18 PR 4, §21):

- Executing or verifying RED/GREEN commands mechanically (the linter validates declared evidence shape; command execution stays in Build) — behavioral judging of evidence quality is spec-judge territory
- Per-task independent review (Increment 5); traceability matrix (Increment 6); commit policy (Increment 7)
- Forcing TDD on pure documentation (§21 explicitly forbids) — that is exactly what the exception path is for
- Retrofitting archived reports; Enforce-mode changes to risk-profile rules (still Observe/Warn)
- Increments 5–9

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; Step 5e parity | Repackage before ship |
| Technical | Deterministic linter; new rules parse declared fields only | RED-validity is skill conduct + evidence shape, not command execution |
| Compatibility | New rules fire only on schema-v2 reports WITH a Risk Level row — both markers shipped by Increments 1–2 | Pre-Inc2 reports untouched (adoption warning path preserved) |
| Compatibility | `dirty`/`missing`/high-critical-TDD-skip are fail-closed; medium stays WARN | §17.2 boundary respected |
| Process | Dogfooding under `/auto`; this run's own report (Risk Level medium, TDD Mode off) exercises the WARN path live | The medium+off WARN will appear on our own gate — visible, non-blocking |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/` (build_report.py + cli + tests), `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`, `.claude/skills/sdd-build/SKILL.md`, `.claude/commands/workflow/build.md`, `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`, `tests/` | Framework/tooling |
| **KB Domains** | `python`, `testing` | Rule parsing + pytest patterns |
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
    - "blast_radius medium: extends the build-report contract consumed by Build/Ship/Autopilot gates"
    - "no elevation floor applies; new FAIL paths are scoped to v2 reports that already declare high/critical risk"
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
| A-001 | The `Risk Level` metadata row's level token is extractable deterministically (first word before any parenthetical) | Needs a stricter row format in the template; additive tweak | [ ] |
| A-002 | Extending `BuildReportContract` (constructor params + 2 rules) stays within the established pattern — no engine change | Larger refactor; contradicts three increments of precedent | [ ] |
| A-003 | High/critical + off → FAIL is acceptable without an Observe ramp because BOTH markers (schema v2, Risk Level row) are new-artifact opt-ins | Would need a WARN phase first; single-line severity change | [ ] |
| A-004 | Exception categories as a flat list of tokens suffice (§10.3's approved_by_policy collapses into category membership) | Category metadata could be added later — additive | [ ] |
| A-005 | `--no-tdd` is skill/command conduct (recorded justification in the report) — the linter checks the outcome (mode vs risk), not the flag | If mechanical flag validation is wanted later, report metadata can gain a row — additive | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §10.1–10.2 verbatim: opt-in only, unvalidated evidence, no exception path |
| Users | 3 | Three personas, pains tied to the matrix row, gate inputs, and the free-text `n/a` hole |
| Goals | 3 | Effective-mode formula, risk_policy table, --no-tdd constraints, exception schema — all 1:1 from §10 |
| Success | 3 | Numbered per-rule test floors; legacy paths pinned |
| Scope | 3 | Mechanical-execution boundary explicit; each deferral owned by an increment |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. Deferred *how* decision: exact parsing of the Risk Level token and the exception-row grammar (`exception: <category> — <verification>`) — Design fixes both shapes against A-001/A-004.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial version — extracted from the incremental-improvements plan §10/§18 (PR 4 scope) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_RISK_DRIVEN_TDD.md`
