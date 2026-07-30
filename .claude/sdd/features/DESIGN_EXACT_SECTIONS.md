# DESIGN: Exact Sections

> One shared addressing module returns EVERY exact-slug match for a fixed-name section; the build contract scans the union of matches (fail-closed) and FAILs duplicates — prefix matching leaves the codebase entirely, so no heading variation can redefine a gate's scope.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXACT_SECTIONS |
| **Date** | 2026-07-30 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_EXACT_SECTIONS.md](DEFINE_EXACT_SECTIONS.md) |
| **Status** | Ready for Build |
| **Risk Level** | medium (echo from DEFINE) |

---

## Architecture Overview

```text
                    spec_linter/sections.py   (NEW — single addressing authority)
                    ─────────────────────────────────────────────────────────────
                    slug(text)                      canonical slugging
                    Section(slug,title,line,body)   typed, position-preserving
                    find_sections(artifact, slugs)  ALL exact matches, ##-level
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
  build_report.py parse()                              MD.duplicate_contract_section
  6 fixed-name sections, each via find_sections:        len(matches) > 1  → FAIL
  review_verdict · task_execution · tdd_evidence        (names section + heading lines)
  task_reviews · traceability_matrix · workflow_metrics
        │
        └─► row scans read the UNION of matching bodies (fail-closed: an open
            blocking row in ANY copy blocks); the metrics yaml fence reads the
            FIRST match deterministically (duplicates already FAIL)

  _section_after / _section_exact  →  DELETED (0 call sites remain)
```

The failure direction inverts: previously a decoy could *shrink* a gate's scope to nothing (false PASS); now an unexpected heading simply is not the section (required-section FAIL) and a duplicate is an explicit FAIL.

---

## Components

| Component | Change |
|-----------|--------|
| `spec_linter/sections.py` | NEW: `slug()`, `Section` dataclass, `find_sections()` — exact-slug, ##-level, all matches, with heading line numbers |
| `contracts/build_report.py` | All 6 fixed-name sections addressed through the shared module; union-body row scans; `_section_after`/`_section_exact`/local `_slug` deleted; new `MD.duplicate_contract_section` rule; TDD sanctioned heading set |
| `WORKFLOW_CONTRACTS.yaml` | v3.18.0 + history (no vocabulary change) |
| `tools/spec-linter/tests/` | RED-first §6.6 grid + duplicate tests + archived-report dogfood |
| `tests/test_workflow_metrics.py` | History pin → 3.18.0 at [0] |

---

## Key Decisions

### Decision 1: `find_sections` returns ALL matches; the contract decides how to combine `[ASSUMED 0.92]`

A lookup that returns `Section | None` cannot express "duplicated" — the very condition §6.4 item 3 requires. Returning the full list makes duplicate detection a property of the data, not a second scan, and lets each rule pick its combination policy explicitly. Rejected: `find_one()` raising on duplicates — exceptions for a lint condition would bypass the Finding pipeline that consumers depend on.

### Decision 2: Row scans read the UNION of duplicate bodies; the metrics fence reads the FIRST `[ASSUMED 0.90]`

For findings/rows, union is the fail-closed choice: an open Critical in *any* copy of the section must block, so a duplicate can never be a hiding place while the duplicate rule reports the structural problem. For the metrics yaml fence a union makes no sense (two fences are not one document), so the first match is used deterministically — the duplicate FAIL already blocks that report.

### Decision 3: TDD Evidence has a closed two-variant sanctioned set `[ASSUMED 0.90]`

The template ships `## TDD Evidence (required when TDD Mode != off)`; hand-written reports use `## TDD Evidence`. Both are legitimate exact names, and the archived corpus was surveyed: all TDD-bearing archives use the full template variant. The set is closed to those two — `TDD Evidence Notes` is not the section. Rejected: prefix matching for this one section (the exact bug being fixed) and normalizing away parentheticals (an open-ended rule that would re-admit decoys).

### Decision 4: `MD.duplicate_contract_section` is always-on, not family-armed `[ASSUMED 0.91]`

It guards the addressing of sections the core rules read (review verdict, task execution), which are never opt-in. Opt-in families' sections are covered by the same rule for free — a duplicated `## Task Reviews` is a structural defect regardless of whether its verdict rules are armed.

### Decision 5: Section bodies use a SAME-LEVEL boundary and ignore fenced code `[ASSUMED 0.93]` *(added in fix-round 1)*

The first draft used the standard Markdown boundary (next heading of the same **or higher** level) with no fence awareness. Review reproduced two live bypasses from that choice: a stray `# x` line parked above an unresolved Critical row truncated the section (deliberate), and — with no adversarial intent at all — a `# TODO: ...` comment inside a quoted ```bash``` snippet did the same, because a line-anchored regex cannot tell code from prose. Both produced PASS on a report carrying an OPEN Critical.

Therefore: a body runs to the next heading at **exactly** the same level, and fenced (``` / ~~~) regions are excluded from heading scanning entirely. **Disclosed trade-off:** a level-3 lookup can overrun its parent section, and a stray top-level heading stays inside the body — deliberately erring toward a LARGER scope, which can only add findings, never hide one. Rejected: standard same-or-higher semantics (the reproduced bypass) and fence-awareness alone (leaves the deliberate `# x` attack open).

### Decision 6: The monitored set must EQUAL the trust set `[ASSUMED 0.93]` *(fix-round 3)*

Review reproduced a third bypass: `MD.duplicate_contract_section` watched only the six sections the contract READS, while `_BOUNDARY_SLUGS` trusted 21 to end a section — so the other 15 could truncate a scope with nothing raising an alarm (`## Files Created` parked above an unresolved Critical → PASS, and worse, MOVED rather than duplicated so no duplicate existed to find). Duplicate monitoring now covers the whole vocabulary. The reviewer's formulation of the invariant is the one to carry forward: *the set of constructions trusted to delimit evidence must equal the set monitored for abuse of that trust.*

### Decision 7: One opaque-region scanner, shared by headings AND rows `[ASSUMED 0.92]` *(fix-round 4)*

The row-level safety net initially ran its own fence-unaware raw scan, so a findings table quoted inside a ```markdown fence (documenting "what a bad row looked like") blocked a clean report. `content_lines()` was extracted from `sections.py` and is now the single implementation of opacity for both heading detection and row scanning. Rejected: a second fence tracker in the contract module — two implementations of the same rule is how they drift.

### Decision 8: Fragment inheritance is scoped by column WIDTH `[ASSUMED 0.90]` *(fix-round 4)*

A table split by intervening content is one logical table, so a headerless fragment inherits the nearest preceding header — that is what keeps the severed-row bypass closed. Unscoped, inheritance reached across unrelated sections and made a decision log whose author omitted its header inherit "findings" identity (a clean report spuriously blocked). Inheritance therefore requires the fragment's column count to match the inherited header's: a genuine continuation preserves width, an unrelated table does not. **Disclosed cost:** a severed row padded to a different width escapes (R-5 in the PR B handoff).

Gate D: all eight ≥ 0.90 — no pauses. (Interactive run; threshold 0.80.)

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-MOD-001
      title: sections.py shared addressing module — TDD
      requirements: [REQ-001]
      depends_on: []
      files: { create: [tools/spec-linter/spec_linter/sections.py], modify: [], tests: [tools/spec-linter/tests/test_sections.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: module, commit: "feat(spec-linter): shared exact-section addressing" }
      acceptance: ["slug() matches prior behavior; find_sections returns all exact ##-level matches with title/line/body; decoy and demoted headings never match; body ends at the next ## heading"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_sections.py -q  # written first, module absent"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_sections.py -q"
    - id: TASK-MIG-001
      title: Migrate 6 sections + delete prefix API + duplicate rule — TDD
      requirements: [REQ-002, REQ-003, REQ-004, REQ-005]
      depends_on: [TASK-MOD-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: contract, commit: "fix(spec-linter): exact section addressing closes the review-verdict bypass" }
      acceptance: ["§3.1 decoy repro FAILs; decoy after inert; duplicates FAIL with line numbers and union scan; demoted heading -> required_section FAIL; TDD two-variant set; 0 _section_after/_section_exact call sites"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_build_report_contract.py -q"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-TEST-001
      title: Archived-report dogfood + §6.6 resolution grid
      requirements: [REQ-007, REQ-008]
      depends_on: [TASK-MIG-001]
      files: { create: [], modify: [tools/spec-linter/tests/test_build_report_contract.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): archived-report dogfood for exact sections" }
      acceptance: ["every archived BUILD_REPORT_*.md with a Schema Version row lints without addressing findings; valid/invalid resolution grammar pinned; the named §3.1 repro test exists"]
      verification:
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_build_report_contract.py -q"
    - id: TASK-DATA-001
      title: v3.18.0 + history entry
      requirements: [REQ-006]
      depends_on: [TASK-MIG-001]
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: data, commit: "chore(sdd): v3.18.0 exact-section addressing" }
      acceptance: ["version 3.18.0 in header+field; history entry names MD.duplicate_contract_section and the removed prefix API; prior entries intact"]
      verification:
        green: "python3 -c 'import yaml; d=yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\")); assert d[\"version\"]==\"3.18.0\"'"
    - id: TASK-PIN-001
      title: Root history pin
      requirements: [REQ-006]
      depends_on: [TASK-DATA-001]
      files: { create: [], modify: [tests/test_workflow_metrics.py], tests: [tests/test_workflow_metrics.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: pin, commit: "test(sdd): v3.18.0 history pin" }
      acceptance: ["history[0] is 3.18.0 naming the addressing change; 3.17.0 pinned at [1]"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_workflow_metrics.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-MOD-001 | tools/spec-linter/tests/test_sections.py | unit |
| 2 | REQ-002 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 3 | REQ-003 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 4 | REQ-004 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 5 | REQ-005 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 6 | REQ-006 | MUST | TASK-DATA-001, TASK-PIN-001 | tests/test_workflow_metrics.py | contract |
| 7 | REQ-007 | SHOULD | TASK-MOD-001, TASK-MIG-001, TASK-TEST-001 | both linter test files | unit |
| 8 | REQ-008 | COULD | TASK-TEST-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `tools/spec-linter/tests/test_sections.py` | Create | RED-first module tests | (general) | None |
| 2 | `tools/spec-linter/spec_linter/sections.py` | Create | Shared addressing | (general) | 1 |
| 3 | `tools/spec-linter/tests/test_build_report_contract.py` | Modify | RED-first §6.6 grid + duplicates + dogfood | (general)/@test-generator | 2 |
| 4 | `tools/spec-linter/spec_linter/contracts/build_report.py` | Modify | Migration + duplicate rule | (general) | 3 |
| 5 | `WORKFLOW_CONTRACTS.yaml` | Modify | v3.18.0 + history | (general) | 4 |
| 6 | `tests/test_workflow_metrics.py` | Modify | History pin | @test-generator | 5 |

---

## Agent Assignment Rationale

| Agent | Files | Why |
|-------|-------|-----|
| (general) | 1–5 | Parser module + contract migration following established rule patterns — no specialist gap (autoprovision sensor: 0 citations) |
| @test-generator | 3 (dogfood part), 6 | Corpus-driven test generation and the pin restructure |

---

## Code Patterns

### The shared module (file 2)

```python
@dataclass(frozen=True, slots=True)
class Section:
    slug: str
    title: str
    line: int          # 1-indexed heading line, for error messages
    body: str          # text up to the next ##-level heading

def find_sections(artifact: str, slugs: set[str], *, level: int = 2) -> list[Section]:
    """EVERY heading at `level` whose slug is IN `slugs`, in document order.
    Exact slug equality only — a prefix like 'review_verdict_notes' is a
    different section, and a demoted '### X' is not this section at all."""
```

### Migration + duplicate rule (file 4)

```python
_FIXED_SECTIONS = {
    "review_verdict": {"review_verdict"},
    "task_execution": {"task_execution_with_agent_attribution"},
    # Closed two-variant set: the template's parenthetical heading and the bare one
    "tdd_evidence": {"tdd_evidence", "tdd_evidence_required_when_tdd_mode_off"},
    "task_reviews": {"task_reviews"},
    "traceability_matrix": {"traceability_matrix"},
    "workflow_metrics": {"workflow_metrics"},
}

matches = {key: find_sections(artifact, slugs) for key, slugs in _FIXED_SECTIONS.items()}
union = lambda key: "\n".join(s.body for s in matches[key])          # fail-closed scans
duplicates = {key: ms for key, ms in matches.items() if len(ms) > 1}  # MD.duplicate_*
```

### Schema Evolution Plan

No schema change — v3.18.0 records behavior hardening (addressing + duplicate detection). Rollback = revert the PR; prior prefix tolerance returns. Archived reports are unaffected (surveyed: single sections, template-exact TDD heading).

---

## Data Flow

1. `parse()` resolves all 6 fixed-name sections through `find_sections` →
2. duplicates become `MD.duplicate_contract_section` FAILs (names + line numbers) →
3. row/finding scans read the union of matching bodies; the metrics fence reads the first →
4. existing rules (blocking findings, task completeness, TDD evidence, task reviews, matrix coverage, metrics) run on scopes that no heading variation can redefine.

---

## Integration Points

| Point | Contract |
|-------|----------|
| Required sections | Unchanged (`L2.required_section` still keys on ##-level slugs) — a demoted heading surfaces there |
| Opt-in families | Unchanged arming; the duplicate rule is always-on |
| Legacy reports | Unchanged — no Schema Version row still routes to `_check_legacy` before any addressing rule |
| Plugin | `plugin/tools/spec-linter` regenerated by `./build-plugin.sh`; parity via `tests/test_plugin_parity.py` |
| Remediation program | §16: this is PR A, which blocks PRs B–I; PR F later consolidates design/define parsers onto this module |

---

## Testing Strategy

| Layer | Tests |
|-------|-------|
| Unit — module (TDD RED-first) | slug equivalence with the prior implementation; all-matches ordering; body boundary at the next `##`; decoy/demoted non-matching; empty-body section |
| Unit — contract (TDD RED-first) | The §6.6 grid: decoy before/after, two exact sections, `###` demotion, open Critical, open Important, `fixed in <sha>`, invalid look-alikes, canonical PASS; duplicate for each of the 6 sections; union-scan proof (blocking row only in the second copy) |
| Dogfood | Every archived `BUILD_REPORT_*.md` with a Schema Version row lints with no addressing findings (§6.7 last bullet) |
| Contract | v3.18.0 history pin (root suite) |
| Regression | Full suites + plugin parity |

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Duplicated fixed-name section | `MD.duplicate_contract_section` FAIL naming section + heading lines; scans still union (never a hiding place) |
| Section absent | Existing paths: required-section FAIL, or the family's own missing/adoption rule |
| Decoy heading | Simply not the section — inert; if the real section is absent too, required-section FAIL fires |

---

## Configuration

None added. Addressing is structural, not configurable — making it configurable would recreate the bypass as a setting.

---

## Security Considerations

Closes a gate-integrity bypass: the review verdict is the human-judgment record autopilot's Gate R and ship depend on; a report that can hide an open Critical undermines every downstream decision.

---

## Observability

Duplicate findings carry the heading line numbers; section-scoped findings keep their existing fields. `Section.line` exists precisely so future rules can point at a heading.

---

## Pipeline Architecture (if applicable)

Not applicable — framework tooling.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-30 | design-agent | Initial — remediation spec §6 (PR A) under autopilot conduct |

---

## Next Step

`/build .claude/sdd/features/DESIGN_EXACT_SECTIONS.md` (autopilot continues)
