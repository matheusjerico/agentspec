# DEFINE: Exact Sections

> Close the Critical parser bypass (remediation spec §6, PR A): every fixed-name contract section is addressed by exact slug from a shared parsing module, duplicated contract sections are FAILs, and `_section_after` prefix matching leaves the gate path — a `## Review Verdict Notes` decoy can no longer hide an open Critical finding.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXACT_SECTIONS |
| **Date** | 2026-07-30 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 15/15 |

**Source:** `docs/superpowers/specs/2026-07-29-agentspec-architecture-remediation-design.md` §6 (Remediação 1 — Critical), §4.2 (exact addressing principle), §15 PR A, §16 (blocks every other remediation). Phase 0 carried by the ratified spec. Baseline: post-LINTER_FAIL_CLOSED main (`f5292fc`).

---

## Problem Statement

The spec's independent revalidation reproduced the bypass on the post-LINTER_FAIL_CLOSED main: a `## Review Verdict Notes` decoy placed before the real section, with an open Critical finding in the real one, still produced PASS (§3.1). Root cause (§6.3): `_section_after` prefix matching remained on critical surfaces — `Review Verdict`, `Task Execution with Agent Attribution`, `TDD Evidence` — so the FIRST heading whose slug merely starts with the target becomes the scanned scope, and the real section's open findings are never read. There is also no duplicate detection: two exact `## Review Verdict` sections are legal today, and only the first is scanned.

---

## Target Users

| ID | User | Role | Pain Point |
|----|------|------|------------|
| - | AgentSpec maintainer (Matheus) | Trusts gate verdicts | A report author (or generator bug) can retitle/duplicate a heading and hollow out the review gate |
| - | Autopilot runs | Gate R/L consume the verdict | The blocking-findings rule reads whatever section the prefix match found — possibly a decoy |
| - | Remediation program (PRs B–I) | §16: PR A blocks all | Every later remediation builds on trustworthy section addressing |

---

## Goals

What success looks like (prioritized):

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | **MUST** | New shared parsing module (`spec_linter/sections.py`): slugging + exact-slug section lookup returning EVERY match with title, heading line number, and body — the single addressing authority for fixed-name contract sections |
| REQ-002 | **MUST** | `build_report.py` migrates its three prefix-matched surfaces — `Review Verdict`, `Task Execution with Agent Attribution`, `TDD Evidence` — to exact addressing via the shared module; `_section_after` is removed from the module (no gate path uses prefix matching anymore) |
| REQ-003 | **MUST** | TDD Evidence's sanctioned heading set is closed and explicit: the template's full heading (`TDD Evidence (required when TDD Mode != off)`) and the bare `TDD Evidence` — both exact; anything else (e.g. `TDD Evidence Notes`) is not the section |
| REQ-004 | **MUST** | New generic rule `MD.duplicate_contract_section` (FAIL): more than one exact match for any fixed-name contract section — including across a sanctioned-set's variants — names the section and the duplicate heading line numbers; the findings scan uses the UNION of duplicates (fail-closed: an open blocking row in any copy blocks) |
| REQ-005 | **MUST** | Wrong-level headings stay invisible to addressing (### is not ##) and therefore surface as the existing `L2.required_section` FAIL for required sections — covered by regression tests, not new code |
| REQ-006 | **MUST** | Version bump v3.18.0 + history; plugin parity; archived v2 reports remain valid (dogfood: lint the two archived metrics-era reports, exit 0) |
| REQ-007 | **SHOULD** | TDD RED-first tests (§6.6 grid): decoy before / decoy after / two exact sections / demoted `###` / open Critical in the real section / open Important / valid `fixed in <sha>` resolution / invalid look-alike resolution / canonical report PASS |
| REQ-008 | **COULD** | The original spec repro (`## Review Verdict Notes` + real section with open Critical) as a named regression test quoting §3.1 |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] 0 `_section_after` call sites (function deleted); 3 surfaces migrated to exact addressing
- [ ] `MD.duplicate_contract_section` fires for every duplicated fixed-name section (6 sections covered: review_verdict, task_execution, tdd_evidence, task_reviews, traceability_matrix, workflow_metrics) — ≥3 duplicate tests
- [ ] The §3.1 repro FAILs (was PASS) — ≥9 tests from the §6.6 grid
- [ ] Both suites green (root ≥172, spec-linter ≥238 before additions); build + parity exit 0; 2 archived reports lint exit 0

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Decoy before | `## Review Verdict Notes` then real section with open Critical | lint | FAIL (blocking finding read from the real section) |
| AT-002 | Decoy after | real section then decoy | lint | Real section scanned; decoy inert |
| AT-003 | Two exact sections | duplicated `## Review Verdict` | lint | `MD.duplicate_contract_section` FAIL naming lines; union scan still reads blocking rows |
| AT-004 | Demoted heading | `### Review Verdict` only | lint | `L2.required_section` FAIL |
| AT-005 | Open Critical/Important | real section, OPEN resolution | lint | FAIL (existing rule, now decoy-proof) |
| AT-006 | Valid resolution | `fixed in abc1234` | lint | No blocking finding |
| AT-007 | Invalid look-alike | `fixed? no` / `Fixed - actually not` | lint | Blocks (existing fail-closed regex, regression-pinned) |
| AT-008 | TDD heading set | full template heading AND bare heading | lint | Both address the section; `TDD Evidence Notes` does not |
| AT-009 | Canonical + archived reports | valid fixture + 2 archived v2 reports | lint | PASS / exit 0 |
| AT-010 | Parity + history | build + version_history | run + documental test | Exit 0; v3.18.0 entry present |

---

## Out of Scope

- The structural table parser and `MalformedRow` model (§7, PR B)
- Full parser/model consolidation across contracts (§11, PR F) — the shared module starts with section addressing only
- Design/define-side section addressing changes (their prefix uses are v1/v2 discovery by design; migration rides PR F)
- PR Readiness executable validation (§8, PR D), test-all gate (§9, PR C), enforcement rollout (§10, PR G)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; plugin parity via build | Repackage before ship |
| Compatibility | Archived v2 reports (template-conform, single sections, full TDD heading) must stay valid — §6.7 | Dogfood lint in tests |
| Process | TDD required (medium-high risk: the review gate itself); RED before GREEN | Evidence in the report |
| Process | Program conduct (user-ratified 2026-07-30): each remediation ships → PR → verified merge → next, A→I order | PR A merges before PR B starts |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/spec_linter/sections.py` (new), `contracts/build_report.py`, `tools/spec-linter/tests/`, `WORKFLOW_CONTRACTS.yaml` (version+history), root history pin | Linter code + tests + version data |
| **KB Domains** | `python`, `testing` | Parser patterns |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

No YAML vocabulary change. The new `MD.duplicate_contract_section` rule joins the BR-family arming implicitly (it guards the sections those families read; the review/task-execution surfaces are core, always-on).

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: medium
  reasons:
    - "blast_radius medium-high: the review gate's own scoping changes; every lint of every report crosses it"
    - "the change REMOVES tolerance — failure mode is false FAIL on nonconforming reports, never false PASS"
  dimensions:
    data_loss: none
    security: low
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
| A-001 | All archived v2 reports use single, template-exact headings (full TDD parenthetical) | Add their exact variant to the sanctioned set, or a migration diagnostic per §6.7 | [ ] |
| A-002 | The three migrated surfaces are the only `_section_after` call sites in build_report.py | Migrate the stragglers in the same pass — the function is deleted, so the compiler finds them | [ ] |
| A-003 | Union-scanning duplicates cannot double-count a finding into a wrong rule (rows are per-section scans feeding independent rules) | De-duplicate scan results by row identity | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §3.1 live repro + §6.3 root cause, verbatim |
| Users | 3 | Gate-trust, autopilot, and program-dependency pains concrete |
| Goals | 3 | §6.4 items 1–6 map 1:1 to REQ IDs incl. the TDD-heading nuance |
| Success | 3 | Numbered floors: 0 call sites, 6 sections, §6.6 grid, archived dogfood |
| Scope | 3 | PR B/C/D/F/G boundaries named per §15/§16 |
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
| 1.0 | 2026-07-30 | define-agent | Initial — remediation spec §6 ratified as Phase 0 under the /auto pre-ignition interview |
