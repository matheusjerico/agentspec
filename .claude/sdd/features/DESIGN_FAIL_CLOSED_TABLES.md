# DESIGN: Fail Closed Tables

> One parser turns every recognised table line into a `ParsedRow` **or** a `TableError` — never nothing. With the "silently discarded" category deleted by construction, the remaining table bypasses have nowhere to live, and closed vocabularies turn "unrecognised token" from an escape hatch into a FAIL.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FAIL_CLOSED_TABLES |
| **Date** | 2026-07-30 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_FAIL_CLOSED_TABLES.md](DEFINE_FAIL_CLOSED_TABLES.md) |
| **Status** | Ready for Build |
| **Risk Level** | high (echo from DEFINE) |

---

## Architecture Overview

```text
  sections.content_lines()            ← opacity (fences, HTML comments) — PR A owns it
            │
            ▼
  spec_linter/markdown/tables.py      ← NEW: the only table parser in the codebase
            │
            │  parse_tables(section_name, body) -> list[ParsedTable]
            │
            │  INVARIANT: every recognised table line becomes a ParsedRow, a
            │  TableError, or BOTH. There is no third outcome. "Dropped
            │  without a diagnostic" is not a code path that exists.
            ▼
  ParsedTable(section, headers, header_line, rows, errors)
            │
     ┌──────┴────────────────────────────────┐
     ▼                                       ▼
  design_phase.py                     build_report.py
  matrix                              matrix · task reviews · task execution ·
                                      review findings · TDD evidence
     └──────────────┬────────────────────────┘
                    ▼
        contracts map TableError -> Finding
        (the parser never decides severity)
```

Nine hand-rolled row scans and seven copies of `strip("|").split("|")` are deleted. Cell splitting becomes escape-aware in exactly one place.

---

## Components

| Component | Change |
|-----------|--------|
| `spec_linter/markdown/__init__.py` | Public API: `parse_tables`, `ParsedTable`, `ParsedRow`, `TableError`, `TableErrorKind` |
| `spec_linter/markdown/tables.py` | NEW parser: block grouping, escape-aware cell split, header validation, per-row validation, the eight error kinds |
| `contracts/build_report.py` | Five surfaces re-plumbed onto `ParsedTable`; `MD.table_malformed` + `MD.html_table_forbidden`; closed severity vocabulary; `_NUMBERED_ROW`/`_TABLE_ROW`/`_SEPARATOR_ROW` and every local cell split deleted |
| `contracts/design_phase.py` | Matrix re-plumbed onto the same parser; its own `_NUMBERED_ROW` deleted |
| `WORKFLOW_CONTRACTS.yaml` | v3.20.0: `table_contract` block (severity vocabulary, resolution-column names, required cells per surface) + history |
| `tools/spec-linter/tests/` | §7.8's 14 cases, the 8 kinds, R-1..R-5 regressions, corpus dogfood |

---

## Key Decisions

### Decision 1: Parse, never filter — the invariant that ends the bypass class `[ASSUMED 0.95]`

Every recognised table line produces a `ParsedRow`, a `TableError`, or both. A malformed row is still returned in `rows` (with whatever cells it had) *and* recorded in `errors`, so a consumer can never mistake "malformed" for "absent". §7.3 names this as the root cause; PR A proved the alternative empirically — four rounds, each finding another way to be silently dropped.

**Totality (adopted from the Gate J advisory):** the parser is a TOTAL function — no input string may raise. Malformed, truncated, adversarial or binary-ish input yields `TableError`s, never a stack trace. A parser that crashes turns a lint into an outage and, worse, into an *unknown* verdict; "never raises" is the same fail-closed reflex as "never discards", applied to control flow. Pinned by a test that feeds hostile inputs and asserts only that nothing propagates.

**Why this converges where PR A did not:** the earlier fixes enumerated *shapes* that must not be discarded, so every round found an unenumerated shape. Here the discard behaviour itself is removed, so there is no shape left to find. A review finding can then only be (a) a regression — some code path still filters — which is a local bug fix, or (b) a genuinely new *invariant*, which is a DESIGN change made once. It cannot be "another instance of the same class".

### Decision 2: Closed vocabularies, unknown means FAIL `[ASSUMED 0.93]`

Severity words, resolution-column names and exception categories become closed sets in `WORKFLOW_CONTRACTS.yaml`. An unrecognised token is `invalid_identifier` → FAIL, not a silent non-match. This is what kills R-4 (`Blocker`, homoglyphs) and R-1 (`Status` vs `Resolution`) at the root rather than by adding one more accepted spelling. Unicode is NFKC-normalised before matching so a Cyrillic `С` cannot masquerade as `C`.

### Decision 3: Unparseable structure is FAIL, never invisibility `[ASSUMED 0.92]`

A raw `<table>` in a contract artifact is `MD.html_table_forbidden` (FAIL), not something to parse. Rejecting is cheap, total, and matches §4.1; parsing HTML would add a second grammar and a second set of shape assumptions — exactly the debt this increment exists to pay off.

### Decision 4: One parser, one cell splitter `[ASSUMED 0.94]`

Seven copies of `strip("|").split("|")` exist today; the escaped-pipe bug (AT-004) lives in all of them. The parser owns splitting, honours `\|`, and both phase contracts consume it. §7.9's last acceptance bullet ("o parser é compartilhado entre Design e Build") is verified by grep in the test suite.

### Decision 5: The parser reports structure; the contract decides severity `[ASSUMED 0.93]`

`TableError` carries kind, section, line, expected/found counts and the raw line — no `Level`. Mapping to FAIL/WARN stays in the contracts, where severity has always been policy. This keeps the parser reusable by PR E/F without them inheriting build-phase policy.

Gate D: all five ≥ 0.90 — no pauses. (Interactive run; threshold 0.80.)

---

## Gate J disposition (advisory, cross-model)

`spec-judge` returned FAIL with four concerns. Adopted one; the other three are
template-driven and do not hold for a single-shot, pure-function CLI parser —
recorded rather than silently ignored, and rather than pretending to fix them.

| Concern | Disposition |
|---|---|
| Parser exceptions beyond exit 2 | **Adopted** — reframed as parser totality (Decision 1); a crash is an unknown verdict |
| Concurrency / race conditions | Not applicable — single process, no shared mutable state, no concurrent parsing |
| Retries / timeouts | Not applicable — no network or I/O beyond reading the artifact already in memory |
| Secrets handling | Not applicable — the parser handles Markdown tables, never credentials |

## Convergence Criterion (how this run ends)

Written into the DESIGN deliberately, because the previous increment's fix loop ran four rounds. The review is to be asked to attack **the invariant**, not to enumerate Markdown shapes. A finding is then classified before it is fixed:

| Class | Meaning | Response | Bounded by |
|---|---|---|---|
| **Regression** | A code path still filters, or a vocabulary is not consulted | Local fix + regression test | Countable: the parse sites are enumerable (grep) |
| **Invariant gap** | The invariant as stated does not cover a real surface | DESIGN change, once, then re-derive | At most one per surface (6 surfaces, §7.5) |
| **Instance** | "Here is another Markdown shape" | NOT a fix: verify the invariant already covers it, add the case to the grid | Zero code change |

If a round produces only Instances, the feature is done. If a round produces an Invariant gap, that is a real design miss and worth the round. This is the exit condition — not a round count.

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-PARSER-001
      title: markdown/tables.py — model + parser (parse-never-filter) — TDD
      requirements: [REQ-001, REQ-002]
      depends_on: []
      files: { create: [tools/spec-linter/spec_linter/markdown/__init__.py, tools/spec-linter/spec_linter/markdown/tables.py], modify: [], tests: [tools/spec-linter/tests/test_markdown_tables.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: high
      execution: { tdd: "required", parallel_group: parser, commit: "feat(spec-linter): structural table parser" }
      acceptance: ["every recognised line yields ParsedRow and/or TableError; 8 kinds emitted; escaped pipes kept in one cell; headers validated; opacity consumed from sections.content_lines"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_markdown_tables.py -q  # written first, package absent"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_markdown_tables.py -q"
    - id: TASK-DATA-001
      title: table_contract block (vocabularies) + v3.20.0
      requirements: [REQ-007]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: data, commit: "feat(sdd): table_contract vocabularies" }
      acceptance: ["severity_vocabulary (blocking/non-blocking), resolution_columns, required_cells per surface; version 3.20.0 + history; prior entries intact"]
      verification:
        green: "python3 -c 'import yaml; d=yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\")); assert d[\"version\"]==\"3.20.0\" and d[\"table_contract\"]'"
    - id: TASK-BUILD-001
      title: Re-plumb build_report's five surfaces + MD rules — TDD
      requirements: [REQ-003, REQ-004, REQ-005, REQ-006]
      depends_on: [TASK-PARSER-001, TASK-DATA-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/build_report.py, tools/spec-linter/spec_linter/cli.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: high
      execution: { tdd: "required", parallel_group: build-side, commit: "fix(spec-linter): build tables fail closed" }
      acceptance: ["matrix/task-reviews/task-execution/review-findings/TDD read ParsedTable; MD.table_malformed + MD.html_table_forbidden; closed severity vocabulary with NFKC; R-1..R-5 all FAIL; no local row regex or cell split remains"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_build_report_contract.py -q"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-DESIGN-001
      title: Re-plumb design_phase's matrix onto the shared parser — TDD
      requirements: [REQ-003, REQ-006]
      depends_on: [TASK-PARSER-001]
      files: { create: [], modify: [tools/spec-linter/spec_linter/contracts/design_phase.py], tests: [tools/spec-linter/tests/test_design_phase_contract.py] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "required", parallel_group: design-side, commit: "fix(spec-linter): design matrix fail closed" }
      acceptance: ["matrix reads ParsedTable; TX rules consume errors; local _NUMBERED_ROW deleted; §7.6 within-artifact rules enforced"]
      verification:
        red: "rtk proxy python3 -m pytest tools/spec-linter/tests/test_design_phase_contract.py -q"
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-TEST-001
      title: §7.8 grid + R-1..R-5 regressions + corpus dogfood
      requirements: [REQ-008]
      depends_on: [TASK-BUILD-001, TASK-DESIGN-001]
      files: { create: [], modify: [tools/spec-linter/tests/test_build_report_contract.py, tools/spec-linter/tests/test_design_phase_contract.py], tests: [tools/spec-linter/tests/test_build_report_contract.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: tests, commit: "test(spec-linter): fail-closed table grid" }
      acceptance: ["14 §7.8 cases; 5 named R-regressions; shared-parser grep test; 15 archived reports non-FAIL or explicitly migrated"]
      verification:
        green: "rtk proxy python3 -m pytest tools/spec-linter/tests/ -q"
    - id: TASK-PIN-001
      title: Root history pin
      requirements: [REQ-007]
      depends_on: [TASK-DATA-001]
      files: { create: [], modify: [tests/test_workflow_metrics.py], tests: [tests/test_workflow_metrics.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: pin, commit: "test(sdd): v3.20.0 history pin" }
      acceptance: ["3.20.0 at [0]; chain 3.19.0/3.18.0/3.17.0 pinned"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_workflow_metrics.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit |
| 2 | REQ-002 | MUST | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit |
| 3 | REQ-003 | MUST | TASK-BUILD-001, TASK-DESIGN-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 4 | REQ-004 | MUST | TASK-BUILD-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 5 | REQ-005 | MUST | TASK-BUILD-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 6 | REQ-006 | MUST | TASK-BUILD-001, TASK-DESIGN-001 | tools/spec-linter/tests/test_design_phase_contract.py | unit |
| 7 | REQ-007 | MUST | TASK-DATA-001, TASK-PIN-001 | tests/test_workflow_metrics.py | contract |
| 8 | REQ-008 | SHOULD | TASK-TEST-001 | tools/spec-linter/tests/test_build_report_contract.py | unit |
| 9 | REQ-009 | COULD | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `tools/spec-linter/tests/test_markdown_tables.py` | Create | RED-first parser tests | (general) | None |
| 2 | `tools/spec-linter/spec_linter/markdown/__init__.py` | Create | Public API | (general) | 1 |
| 3 | `tools/spec-linter/spec_linter/markdown/tables.py` | Create | The parser | (general) | 1 |
| 4 | `WORKFLOW_CONTRACTS.yaml` | Modify | `table_contract` + v3.20.0 | (general) | None |
| 5 | `contracts/build_report.py` | Modify | Five surfaces + MD rules | (general) | 3, 4 |
| 6 | `contracts/design_phase.py` | Modify | Matrix | (general) | 3 |
| 7 | `spec_linter/cli.py` | Modify | Wire `table_contract` | (general) | 4 |
| 8 | test files (build/design) | Modify | §7.8 grid + regressions | @test-generator | 5, 6 |
| 9 | `tests/test_workflow_metrics.py` | Modify | History pin | @test-generator | 4 |

---

## Agent Assignment Rationale

| Agent | Files | Why |
|-------|-------|-----|
| (general) | 1–7 | Parser and contract plumbing following the module patterns PR A established — no specialist gap (autoprovision sensor: 0 citations) |
| @test-generator | 8–9 | Grid generation from §7.8 and the pin restructure |

---

## Code Patterns

### The model (file 3)

```python
class TableErrorKind(StrEnum):
    COLUMN_COUNT = "column_count"
    MISSING_HEADER = "missing_header"
    DUPLICATE_HEADER = "duplicate_header"
    EMPTY_REQUIRED_CELL = "empty_required_cell"
    PLACEHOLDER = "placeholder"
    INVALID_IDENTIFIER = "invalid_identifier"
    DUPLICATE_IDENTIFIER = "duplicate_identifier"
    UNEXPECTED_EXTRA_COLUMN = "unexpected_extra_column"


@dataclass(frozen=True, slots=True)
class TableError:
    kind: TableErrorKind
    section: str
    line: int
    expected_cells: int | None
    found_cells: int | None
    raw: str
    detail: str = ""

    def render(self) -> str:            # REQ-009
        return f"{self.section}:{self.line} {self.kind}: {self.detail or self.raw}"
```

### The invariant, expressed in code (file 3)

```python
for line_number, raw in rows:
    cells = _split_cells(raw)           # escape-aware, the ONLY splitter
    if len(cells) != len(headers):
        errors.append(TableError(kind=..., line=line_number, ...))
        # NOTE: the row is still appended below. A malformed row is reported
        # AND kept — never dropped. This is the whole point of the increment.
    parsed.append(ParsedRow(line=line_number, cells=cells, raw=raw))
```

### Schema Evolution Plan

`table_contract` is additive and opt-in like every prior block: absent → the MD rules stay dormant and the contracts fall back to their current behaviour, so a consumer repo upgrades on its own schedule. v3.20.0 records the addition; rollback is reverting the PR.

---

## Data Flow

1. `sections.find_sections` locates the section (PR A) → `content_lines` supplies non-opaque lines →
2. `parse_tables` groups blocks, validates headers, splits cells escape-aware, and emits rows + errors →
3. The contract maps `TableError` → `Finding` with its own severity, and applies the §7.6 within-artifact rules over `ParsedRow` data →
4. Gates L/R/B consume verdicts derived from data that has no silent-discard path.

---

## Integration Points

| Point | Contract |
|-------|----------|
| `sections.content_lines` | Opacity stays PR A's; the parser never re-implements fence/comment tracking |
| `table_contract` | Opt-in: absent block leaves MD rules dormant (same posture as every prior increment) |
| Legacy reports | Unchanged: no Schema Version row still short-circuits to `_check_legacy` before any table rule |
| Plugin | `plugin/tools/spec-linter` regenerated by `./build-plugin.sh`; parity test covers the new package |
| PRs E / F | `ParsedTable` is the surface cross-artifact validation and consolidation will consume |

---

## Testing Strategy

| Layer | Tests |
|-------|-------|
| Unit — parser (TDD RED-first) | §7.8's 14 cases: short row, long row, missing middle column, escaped pipe, placeholder, duplicate REQ, REQ without task, unknown task, MUST without test, MUST result != pass, valid exception, invalid exception, empty matrix, malformed header |
| Unit — kinds | ≥1 test per error kind, asserting section + line in the finding |
| Regression | R-1..R-5 from the PR A handoff, each named and each failing before the change |
| Contract | Shared-parser grep test (0 row regexes left); `table_contract` shape; v3.20.0 pin |
| Dogfood | 15 archived reports non-FAIL, or an explicit migration diagnostic |

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Malformed row | Row kept + `TableError` → contract FAIL naming section and line |
| Unknown severity / column name | `invalid_identifier` → FAIL (closed vocabulary) |
| Raw HTML table | `MD.html_table_forbidden` FAIL — never parsed, never invisible |
| `table_contract` absent | MD rules dormant; prior behaviour preserved |
| Malformed / hostile input | `TableError`, never an exception — the parser is total (Decision 1). A raised exception would be a defect, not a contract path; the CLI's exit-2 envelope remains only for genuinely operational failures (missing file, unreadable contracts) |

---

## Configuration

One new block, `table_contract`: severity vocabulary (blocking + non-blocking), resolution-column names, required cells per surface. No flags, no env vars.

---

## Security Considerations

This closes the last five known ways an unresolved blocking finding can reach PASS. The gate's inputs stop being shape-guessed and start being parsed.

---

## Observability

Every finding carries section + line + expected/found cell counts + the raw row (§7.9: "mensagens apontam seção e linha"), so a failing report tells its author exactly which line to fix.

---

## Pipeline Architecture (if applicable)

Not applicable — framework tooling.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-30 | design-agent | Initial — remediation spec §7 (PR B) + R-1..R-5, with an explicit convergence criterion |

---

## Next Step

`/build .claude/sdd/features/DESIGN_FAIL_CLOSED_TABLES.md` (autopilot continues)
