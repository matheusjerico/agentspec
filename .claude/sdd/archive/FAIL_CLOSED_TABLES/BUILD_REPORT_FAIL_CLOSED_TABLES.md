# BUILD REPORT: Fail Closed Tables

> Implementation report for FAIL_CLOSED_TABLES

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FAIL_CLOSED_TABLES |
| **Date** | 2026-07-30 |
| **Author** | build-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_FAIL_CLOSED_TABLES.md](../features/DEFINE_FAIL_CLOSED_TABLES.md) |
| **DESIGN** | [DESIGN_FAIL_CLOSED_TABLES.md](../features/DESIGN_FAIL_CLOSED_TABLES.md) |
| **Status** | Shipped |
| **Schema Version** | 2 |
| **TDD Mode** | required |
| **Risk Level** | high (echo from DEFINE) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 6/6 (v2 manifest) |
| **Files Created** | 3 new + 6 modified |
| **Lines of Code** | ~900 added |
| **Tests Passing** | 577/577 (185 root + 392 spec-linter) |
| **Agents Used** | 2 specialists + (direct) |

---

## Task Execution with Agent Attribution

| # | Task ID | Task | Agent | Status | Commit | Duration | Notes |
|---|---------|------|-------|--------|--------|----------|-------|
| 1 | TASK-PARSER-001 | markdown/tables.py — model + parser | (direct) | ✅ Complete | 7671bbd | - | TDD RED-first; 12 hostile inputs for totality |
| 2 | TASK-DATA-001 | table_contract + v3.20.0 | (direct) | ✅ Complete | 7671bbd | - | Vocabularies as contract data |
| 3 | TASK-BUILD-001 | Re-plumb build_report's five surfaces | (direct) | ✅ Complete | 7671bbd | - | MD.table_malformed + MD.html_table_forbidden |
| 4 | TASK-DESIGN-001 | Re-plumb design_phase matrix | (direct) | ✅ Complete | 7671bbd | - | Shared parser; grep test enforces it |
| 5 | TASK-TEST-001 | §7.8 grid + R-regressions + dogfood | @test-generator | ✅ Complete | session | - | Corpus dogfood caught a real corpus defect |
| 6 | TASK-PIN-001 | Root history pin | @test-generator | ✅ Complete | session | - | v3.20.0 chain |

**Manifest:** v2 — tasks consumed from the DESIGN Task Manifest (topological order, no inference)

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Agent Key:**
- `@{agent-name}` = Delegated to specialist agent via Task tool
- `(direct)` = Built directly by build-agent (no specialist matched)

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |
|---|-----|----------|-------|-------|-------------------|--------|--------|
| 1 | REQ-001 | MUST | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit | Pass | clean-with-minors |
| 2 | REQ-002 | MUST | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit | Pass | clean |
| 3 | REQ-003 | MUST | TASK-BUILD-001, TASK-DESIGN-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean-with-minors |
| 4 | REQ-004 | MUST | TASK-BUILD-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean |
| 5 | REQ-005 | MUST | TASK-BUILD-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean-with-minors |
| 6 | REQ-006 | MUST | TASK-BUILD-001, TASK-DESIGN-001 | tools/spec-linter/tests/test_design_phase_contract.py | unit | Pass | clean |
| 7 | REQ-007 | MUST | TASK-DATA-001, TASK-PIN-001 | tests/test_workflow_metrics.py | contract | Pass | clean |
| 8 | REQ-008 | SHOULD | TASK-TEST-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean |
| 9 | REQ-009 | COULD | TASK-PARSER-001 | tools/spec-linter/tests/test_markdown_tables.py | unit | Pass | clean |

---

## Task Reviews

| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |
|---|---------|------|----------|---------|----------------------|------------|
| 1 | TASK-PARSER-001 | high | @code-reviewer | clean-with-minors | 0 / 2 | 3/3 |
| 2 | TASK-DATA-001 | medium | @code-reviewer | clean | 0 / 0 | 0/3 |
| 3 | TASK-BUILD-001 | high | @code-reviewer | clean-with-minors | 0 / 2 | 3/3 |
| 4 | TASK-DESIGN-001 | medium | @code-reviewer | clean | 0 / 1 | 1/3 |
| 5 | TASK-TEST-001 | medium | @code-reviewer | clean | 0 / 0 | 0/3 |
| 6 | TASK-PIN-001 | low | @code-reviewer | clean | 0 / 0 | 0/3 |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| @test-generator | 2 | §7.8 grid, R-regressions, corpus dogfood (which caught a real archived-report defect) |
| @code-reviewer | 0 (review) | Three adversarial rounds, every finding reproduced end-to-end before and after |
| (direct) | 7 | Parser package, contract re-plumbing, vocabularies, CLI wiring |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `spec_linter/markdown/tables.py` | ~300 | (direct) | ✅ | The only table parser |
| `spec_linter/markdown/__init__.py` | ~20 | (direct) | ✅ | Public API |
| `tests/test_markdown_tables.py` | ~290 | (direct) | ✅ | 40 tests incl. totality grid |
| `contracts/build_report.py` | ~250 net | (direct) | ✅ | Five surfaces re-plumbed |
| `contracts/design_phase.py` | ~60 net | (direct) | ✅ | Matrix re-plumbed |
| `WORKFLOW_CONTRACTS.yaml` + pin | +30 | (direct) | ✅ | v3.20.0 table_contract |

---

## Verification Results

### Lint Check

```text
shellcheck -S warning (make lint): clean, exit 0
```

**Status:** ✅ Pass

### Type Check

```text
N/A — no mypy gate configured; behavior covered by 392 unit tests
```

**Status:** ⏭️ Skipped

### Tests

```text
root suite:        185 passed
spec-linter suite: 392 passed (334 prior + 58 parser/table rules)
plugin build:      exit 0, parity byte-identical (new markdown/ package included)
archived corpus:   16/16 non-FAIL
regression matrix: 7 bypasses blocked, 4 legitimate constructs clean
```

**Status:** ✅ 577/577 Pass

---

## Review Verdict

> Whole-branch adversarial review — mandatory final step of the build
> (`WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`). Ship refuses
> `dirty` and `missing` verdicts.

| Attribute | Value |
|-----------|-------|
| **Verdict** | clean-with-minors |
| **Reviewer** | @code-reviewer |
| **Diff scope** | merge-base main..HEAD + working tree on feat/auto-fail-closed-tables |
| **Fix rounds used** | 3/2 (override: author=maintainer, rationale=each round found a distinct verdict-flipping Critical, none a repeat) |

| # | Severity | Finding | Location | Resolution |
|---|----------|---------|----------|------------|
| 1 | Critical | A findings table with renamed columns was dropped with no diagnostic — DESIGN promised fail-closed on unknown column names, code delivered it only for unknown values | build_report.py | fixed in fix-round-1: recognition by the closed COLUMN vocabulary, extended with synonyms; a content-based attempt was tried and REMOVED after it reddened three legitimate template sections |
| 2 | Important | An orphaned prose fragment containing "critical" was read as a finding | build_report.py | fixed in fix-round-1: inheritance is positional |
| 3 | Important | An all-dash data row was silently swallowed | markdown/tables.py | fixed in fix-round-1: a separator is a delimiter only in the delimiter position |
| 4 | Important | A double-backslash before a pipe merged two cells, so a cell ending in a backslash swallowed the next column | markdown/tables.py | fixed in fix-round-1: a double backslash is handled as a complete self-escape |
| 5 | Critical | A blank line plus a dash row turned an open finding into a "header" — the simplest bypass in this PR, no heading trick needed | markdown/tables.py | fixed in fix-round-2, then generalised in fix-round-3 |
| 6 | Minor | A reordered severed row names the wrong rule — the build still FAILs via MD.table_malformed, so no verdict flips (the reviewer classified it Warning/non-blocking and confirmed no verdict impact across two rounds) | build_report.py | recorded — fixing it reintroduces the prose false positive of finding 1; deferred to PR F with the reviewer's suggested formulation |
| 7 | Critical | Finding 5's fix was wired into 1 of 6 `parse_tables` call sites, leaving the same bypass live in the matrix, Task Reviews, Task Execution, TDD Evidence and the design matrix | build_report.py, design_phase.py | fixed in fix-round-3: the tie-breaking VOCABULARY was removed entirely and the ambiguity now resolves structurally for every caller — one path instead of six, and the vocabulary's own substring false positive disappears with it |
| 8 | Minor | R-6: a findings table whose column names fall entirely outside the vocabulary is unrecognised | build_report.py | recorded — remedy is one line of contract data; deferred to PR F |

Closing verdict: **clean-with-minors** — the reviewer independently re-derived the fix mechanism by grep, re-executed all three finding-7 repros from scratch, and extended the corpus measurement to 57 files (DESIGN/DEFINE/templates included) finding zero instances of the shape the new rule changes.

---

## TDD Evidence (required when TDD Mode != off)

> TASK-PARSER-001, TASK-BUILD-001 and TASK-DESIGN-001 carry `tdd: required`
> (high risk: every gate reads these tables).

| # | Task ID | RED (failing first) | GREEN (passing after) |
|---|---------|---------------------|----------------------|
| 1 | TASK-PARSER-001 | `pytest tests/test_markdown_tables.py` → ImportError, package absent; 33 tests written first | 33 passed after the parser landed |
| 2 | TASK-BUILD-001 / TASK-DESIGN-001 | Re-plumbing broke 49 then 33 then 13 tests as each surface moved; each batch diagnosed before fixing | 392 passed |
| 3 | Fix rounds 1–3 | Every reviewer finding reproduced end-to-end against the live contract BEFORE fixing | Named regression test per finding |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Gate J returned FAIL with 4 concerns; 3 did not apply to a single-shot pure-function CLI | 1 adopted (parser totality), 3 dispositions recorded in the DESIGN | +10m |
| 2 | My surgery removed `_parse_manifest` along with the dead matrix parser | Restored from the committed version | +5m |
| 3 | A corpus report used severity `Error`, outside the contract taxonomy | Real defect, corrected (same class as PR A's corpus finding) | +5m |
| 4 | Fix-loop budget (2) exceeded at round 3 | Authorized override recorded (the v3.19.0 grammar built in PR A) | - |
| 5 | Review scope was framed as "attack Markdown grammar" — an unbounded surface with falling marginal value | Maintainer flagged it; scope narrowed to what matters for AgentSpec (silent pass, cry-wolf, regression, promised capability) | - |

---

## Autonomous Decisions

The build phase runs autonomously — it never pauses to ask the user. Every
decision fork reached during the build was resolved by choosing the safest
documented default. This section is the post-run review log: each row is a
fork the build resolved on its own. An empty table means the build hit zero
ambiguity (DESIGN fully pre-decided everything).

| # | Decision Point | Options Considered | Chose | Confidence | Rationale |
|---|----------------|--------------------|-------|------------|-----------|
| 1 | Recognising a findings table with foreign columns | Content sniffing vs closed column vocabulary | Vocabulary | 0.91 | Content sniffing reddened `## Issues Encountered`, `## Autonomous Decisions` and a decoy — by content, a cell that IS the word "Important" is indistinguishable from a finding |
| 2 | Where table errors are collected | Every pipe construct vs mandatory-evidence surfaces + findings tables | Scoped to evidence | 0.90 | `| **Tasks Completed** | 2/2 |` is a template label; flagging it is cry-wolf |
| 3 | Resolving the 2-line ambiguity | Per-surface vocabulary (reviewer's suggestion) vs unconditional structural rule | Unconditional | 0.93 | A vocabulary multiplies config across six sites AND carries a substring false positive; removing it closes all six and deletes the FP class |
| 4 | §7.6 rule 4 (task id in manifest) | Approximate against Task Execution vs defer | Defer to PR E | 0.94 | The manifest lives in DESIGN — it is cross-artifact by construction |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Decisions 6 and 7 added during fix rounds (column-vocabulary-only recognition; unconditional ambiguity resolution) | Two Criticals found by review | Recorded in the DESIGN rather than left implicit |
| `MD.matrix_empty` restated as "no well-formed rows" | Decision 7 made the header-only shape unreachable | §7.6 rule 1 survives with the same intent |
| §7.6 rule 4 not implemented | Cross-artifact (PR E), as the DEFINE scoped | Documented in `_check_matrix_identifiers` |
| One archived report's severity corrected (`Error` → `Important`) | Outside the contract taxonomy; surfaced by the closed vocabulary | Disclosed in the PR description |

---

## Blockers (if any)

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| None | - | - |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Short row | ✅ Pass | `column_count` with section + line |
| AT-002 | Long row | ✅ Pass | `unexpected_extra_column` |
| AT-003 | Missing middle column | ✅ Pass | `column_count` |
| AT-004 | Escaped pipe | ✅ Pass | One cell; `\\` self-escape also covered |
| AT-005 | Placeholder | ✅ Pass | Identifier columns only (free text exempt) |
| AT-006 | Identifiers | ✅ Pass | `MD.duplicate_identifier`; task-in-manifest deferred to PR E |
| AT-007 | MUST coverage | ✅ Pass | Malformed rows now ALSO reach coverage |
| AT-008 | Exceptions | ✅ Pass | Existing grammar preserved |
| AT-009 | Empty and malformed | ✅ Pass | `MD.matrix_empty` (no well-formed rows), `duplicate_header` |
| AT-010 | R-1..R-5 | ✅ Pass | Named tests, both variants each |
| AT-011 | Shared parser | ✅ Pass | Grep test: no row regex or cell split left in either contract |
| AT-012 | Corpus + parity | ✅ Pass | 16/16 non-FAIL; build exit 0 |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Hand-rolled row parsers remaining | 0 | 0 (grep-enforced) | ✅ |
| Realistic bypasses open | 0 | 0 (2 exotic residuals recorded) | ✅ |
| False positives on legitimate reports | 0 | 0 (4 constructs verified) | ✅ |

---

## Workflow Metrics

> Machine-readable run metrics (`WORKFLOW_CONTRACTS.yaml` → `workflow_metrics`,
> schema v1). Values are MEASURED or `{value: null, reason: "..."}` — never
> estimated, interpolated, or copied from a prior run. Ship summarizes this
> block into SHIPPED; it never auto-changes any policy.

```yaml
workflow_metrics:
  schema_version: 1
  feature: "FAIL_CLOSED_TABLES"
  phase_duration_seconds: { value: null, reason: "interactive session carries no wall-clock instrumentation" }
  time_to_first_green_seconds: { value: null, reason: "not instrumented" }
  task_count: 6
  effective_parallelism: 1
  tests_by_type: { unit: 58, contract: 1, documental: 0, integration: 0 }
  reopened_tasks: 3
  fix_rounds: { local: 0, final: 3 }
  findings: { critical: 3, important: 3, minor: 2, by_stage: { task_review: 0, branch_review: 8 } }
  requirements: { must_total: 7, must_verified: 7, excepted: 0 }
  operational_skips: []
  risk_overrides: 0
  tokens_cost: { value: null, reason: "platform does not expose reliable per-run tokens" }
```

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Review Verdict is clean or clean-with-minors
- [x] Contract gate passed: `spec-lint --phase build` exit 0
- [x] TDD evidence recorded (mode: required)
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_FAIL_CLOSED_TABLES.md`
