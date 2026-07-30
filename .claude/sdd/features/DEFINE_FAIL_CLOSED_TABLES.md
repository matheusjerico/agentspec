# DEFINE: Fail Closed Tables

> A shared structural table parser (`ParsedTable`/`ParsedRow`/`TableError`) replaces every hand-rolled row regex in the linter: no recognised row is ever discarded silently, every structural error in mandatory evidence is a FAIL naming section and line, and the five table-grammar bypasses PR A deferred are closed at their root.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FAIL_CLOSED_TABLES |
| **Date** | 2026-07-30 |
| **Author** | define-agent |
| **Status** | Draft |
| **Clarity Score** | 15/15 |

**Source:** `docs/superpowers/specs/2026-07-29-agentspec-architecture-remediation-design.md` §7 (Remediação 2, High — model §7.4, surfaces §7.5, rules §7.6, tests §7.8, acceptance §7.9), §15 PR B, §16 (depends on PR A, merged as #15). Inherits `docs/reviews/2026-07-30-exact-sections-residuals-for-pr-b.md` (R-1..R-5). Baseline: main `71fd13a`.

---

## Problem Statement

Every table scan in the linter is a hand-rolled regex over raw lines, and each one decides on its own what a row is. PR A proved where that leads: five reproduced bypasses remain open (R-1..R-5) — a renamed resolution column, a row stripped of its leading `#`, a raw HTML `<table>`, an unrecognised severity word, and a severed row padded to a different width — each letting an unresolved Critical produce PASS. §7.3 names the root cause: the parsers return only rows they liked, so a contract never learns that a row was found and discarded. The same shape assumption is duplicated across Design and Build (§7.7), so every fix has to be made twice and can drift.

---

## Target Users

| ID | User | Role | Pain Point |
|----|------|------|------------|
| - | AgentSpec maintainer (Matheus) | Trusts gate verdicts | A malformed row is indistinguishable from an absent one; five known bypasses are live today |
| - | Autopilot runs | Gates L/R/B consume table-derived findings | Coverage, review and TDD rules all read tables that can silently drop their most important row |
| - | Later remediations (PRs E, F, G) | Depend on trustworthy table data | §12 cross-artifact validation and §11 consolidation both build on this parser |

---

## Goals

What success looks like (prioritized):

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | **MUST** | New `spec_linter/markdown/` package with the §7.4 model: `ParsedTable(headers, rows, errors)`, `ParsedRow`, `TableError(section, line, expected_cells, found_cells, raw, kind)` — every recognised table region is parsed, never filtered; errors are DATA, not silence |
| REQ-002 | **MUST** | The eight §7.4 error kinds: `column_count`, `missing_header`, `duplicate_header`, `empty_required_cell`, `placeholder`, `invalid_identifier`, `duplicate_identifier`, `unexpected_extra_column` |
| REQ-003 | **MUST** | Parser is shared (§7.9 last bullet): `design_phase.py` and `build_report.py` both consume it; the duplicated `_parse_matrix_rows`, task-review and task-execution row regexes are deleted, and `sections.py`'s opacity (fences, HTML comments) governs which lines the parser sees |
| REQ-004 | **MUST** | Structural errors in MANDATORY evidence are FAIL naming section + line (§7.9): matrices, Task Reviews, Task Execution, Review Findings. Severity stays contract data, not a parser decision |
| REQ-005 | **MUST** | R-1..R-5 closed at the root: resolution-column vocabulary (`resolution`/`status`/…), rows without a leading `#`, unknown severity words (fail-closed on unrecognised vocabulary), width-padded severed rows; raw HTML `<table>` in a contract artifact is an explicit FAIL (§4.1 fail-closed over parsing HTML) |
| REQ-006 | **MUST** | §7.6 within-artifact rules: a present matrix needs ≥1 valid row or a structured "no requirements" declaration; REQ-IDs unique; every referenced task ID exists in the v2 manifest; every MUST has task + test + verification type + result; exceptions use the closed category grammar; a placeholder in a final-status artifact is FAIL |
| REQ-007 | **MUST** | Version bump v3.20.0 + history; plugin parity; the archived corpus stays valid or receives an explicit migration diagnostic |
| REQ-008 | **SHOULD** | TDD RED-first for the §7.8 grid (14 cases) plus the R-1..R-5 repros as named regressions |
| REQ-009 | **COULD** | `TableError.render()` one-line human form reused by every consuming rule's message |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] 1 shared parser package; 0 remaining hand-rolled row regexes in `design_phase.py`/`build_report.py` (grep-verified)
- [ ] 8 error kinds, each with ≥1 unit test; §7.8's 14 mandatory cases all covered
- [ ] R-1..R-5: 5 named regression tests, each failing before the change (repros in the handoff doc)
- [ ] Both suites green (root ≥183, spec-linter ≥334 before additions); build + parity exit 0; archived corpus 15/15 non-FAIL or explicitly migrated

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Short row | matrix row with fewer cells than headers | lint | FAIL `column_count` naming section + line |
| AT-002 | Long row | row with extra cells | lint | FAIL `unexpected_extra_column` |
| AT-003 | Missing middle column | header count vs row misaligned | lint | FAIL `column_count` |
| AT-004 | Escaped pipe | cell containing `\|` | lint | Parsed as ONE cell, no false error |
| AT-005 | Placeholder | `{REQ}` in a final-status artifact | lint | FAIL `placeholder` |
| AT-006 | Duplicate / missing / unknown identifiers | duplicate REQ-ID; REQ without task; task not in manifest | lint | FAIL `duplicate_identifier` / coverage / `invalid_identifier` |
| AT-007 | MUST coverage | MUST without test; MUST with Result != pass | lint | FAIL |
| AT-008 | Exceptions | valid closed-category exception; invalid one | lint | Pass / FAIL |
| AT-009 | Empty and malformed | matrix present but empty; malformed header row | lint | FAIL (`missing_header`/`duplicate_header` as applicable) |
| AT-010 | R-1..R-5 | the five handoff repros | lint | All FAIL |
| AT-011 | Shared parser | grep + import graph | Run | Design and Build consume the same parser; no duplicate row regexes |
| AT-012 | Corpus + parity | 15 archived reports, build | Run | non-FAIL (or explicit migration diagnostic); exit 0 |

---

## Out of Scope

- Cross-artifact validation — Define MUSTs vs the Design matrix, bundle-level rules (§12 / PR E); this increment validates WITHIN an artifact plus the already-available v2 manifest
- `PrReadinessContract` executable readiness (§8 / PR D)
- Test-all / release gate (§9 / PR C) and the enforcement rollout (§10 / PR G)
- Full model consolidation across contracts (§11 / PR F) — this delivers the table layer only
- Rendering HTML tables (REQ-005 chooses fail-closed rejection, not parsing)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; plugin parity via build | Repackage before ship |
| Technical | Opacity is owned by `sections.py` (PR A) | The parser consumes `content_lines()`; it must not re-implement fence/comment tracking |
| Compatibility | Archived corpus must stay valid or get an explicit migration diagnostic (§7.9 precedent from §6.7) | Dogfood test over all 15 reports |
| Process | TDD required (high risk: every gate reads these tables) | RED before GREEN per rule |
| Process | Fix-loop budget 2; exceeding it needs the v3.19.0 authorized override (attributed + justified) | Recorded in the report, never silent |
| Process | Program conduct: ship → PR → verified merge → next; PR B unblocks E and F | PR B merges before PR E starts |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/spec_linter/markdown/` (new), `contracts/{design_phase,build_report}.py`, `tools/spec-linter/tests/`, `WORKFLOW_CONTRACTS.yaml`, root pin | Parser package + migration + contract data |
| **KB Domains** | `python`, `testing`, `pydantic` | Parser models and rule tests |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

`TableError` is the new machine-readable surface: section, line, expected/found cell counts, raw content, kind. Consumers (Design and Build contracts) map errors to findings; the parser never decides severity.

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: high
  reasons:
    - "blast_radius high: every table-derived rule in both phase contracts is re-plumbed onto a new parser"
    - "the corpus and all future artifacts are validated by it; a parser defect is a gate-wide defect"
    - "PR A precedent: shape assumptions in this exact area produced four Criticals and three false positives"
  dimensions:
    data_loss: none
    security: medium
    reversibility: low
    blast_radius: high
    migration: medium
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
| A-001 | The 15 archived reports' tables are structurally well-formed under a strict parser (headers match row widths) | A migration diagnostic path is needed instead of plain validity — §7.9 anticipates this | [ ] |
| A-002 | `content_lines()` opacity plus a table-block grouper is enough context; the parser needs no section awareness of its own | Parser takes a section argument for error attribution — small interface change | [ ] |
| A-003 | Escaped pipes (`\|`) appear in real artifacts and must not split cells | Cell splitting needs escape handling from the start, not as a follow-up (AT-004 pins it) | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §7.3 root cause + five reproduced bypasses inherited with repros |
| Users | 3 | Maintainer/autopilot/downstream-PR pains concrete |
| Goals | 3 | §7.4–7.6 map 1:1 to REQ IDs; R-1..R-5 explicitly assigned |
| Success | 3 | Numbered floors: 1 parser, 0 leftover regexes, 8 kinds, 14 cases, 5 regressions |
| Scope | 3 | PRs C/D/E/F/G boundaries named; HTML policy decided rather than left open |
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
| 1.0 | 2026-07-30 | define-agent | Initial — remediation spec §7 (PR B) + PR A's R-1..R-5 handoff, under the /auto pre-ignition interview |
