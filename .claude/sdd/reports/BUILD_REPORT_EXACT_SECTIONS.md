# BUILD REPORT: Exact Sections

> Implementation report for EXACT_SECTIONS

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXACT_SECTIONS |
| **Date** | 2026-07-30 |
| **Author** | build-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_EXACT_SECTIONS.md](../features/DEFINE_EXACT_SECTIONS.md) |
| **DESIGN** | [DESIGN_EXACT_SECTIONS.md](../features/DESIGN_EXACT_SECTIONS.md) |
| **Status** | Complete |
| **Schema Version** | 2 |
| **TDD Mode** | required |
| **Risk Level** | medium (echo from DEFINE) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 5/5 (v2 manifest) |
| **Files Created** | 2 new + 5 modified |
| **Lines of Code** | ~700 added |
| **Tests Passing** | 517/517 (183 root + 334 spec-linter) |
| **Agents Used** | 2 specialists + (direct) |

---

## Task Execution with Agent Attribution

| # | Task ID | Task | Agent | Status | Commit | Duration | Notes |
|---|---------|------|-------|--------|--------|----------|-------|
| 1 | TASK-MOD-001 | sections.py addressing module | (direct) | ✅ Complete | ac28b30 | - | Rewritten twice across fix rounds; now also owns opacity |
| 2 | TASK-MIG-001 | Migrate 6 sections + duplicate rule | (direct) | ✅ Complete | ac28b30 | - | + boundary vocabulary, + safety net (fix rounds) |
| 3 | TASK-TEST-001 | Archived-corpus dogfood + grid | @test-generator | ✅ Complete | session | - | Found a real defect in a shipped report |
| 4 | TASK-DATA-001 | v3.18.0 + history (+ v3.19.0 override block) | (direct) | ✅ Complete | session | - | 3.19.0→3.15.0 chain verified intact |
| 5 | TASK-PIN-001 | Root history pin | @test-generator | ✅ Complete | session | - | 3.19.0 at [0], chain pinned |

**Manifest:** v2 — tasks consumed from the DESIGN Task Manifest (topological order, no inference)

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Agent Key:**
- `@{agent-name}` = Delegated to specialist agent via Task tool
- `(direct)` = Built directly by build-agent (no specialist matched)

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |
|---|-----|----------|-------|-------|-------------------|--------|--------|
| 1 | REQ-001 | MUST | TASK-MOD-001 | tools/spec-linter/tests/test_sections.py | unit | Pass | clean-with-minors |
| 2 | REQ-002 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean-with-minors |
| 3 | REQ-003 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean |
| 4 | REQ-004 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean-with-minors |
| 5 | REQ-005 | MUST | TASK-MIG-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean |
| 6 | REQ-006 | MUST | TASK-DATA-001, TASK-PIN-001 | tests/test_workflow_metrics.py | contract | Pass | clean |
| 7 | REQ-007 | SHOULD | TASK-MOD-001, TASK-MIG-001, TASK-TEST-001 | both linter test files | unit | Pass | clean-with-minors |
| 8 | REQ-008 | COULD | TASK-TEST-001 | tools/spec-linter/tests/test_build_report_contract.py | unit | Pass | clean |

---

## Task Reviews

| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |
|---|---------|------|----------|---------|----------------------|------------|
| 1 | TASK-MOD-001 | medium | @code-reviewer | clean-with-minors | 0 / 2 | 4/4 |
| 2 | TASK-MIG-001 | medium | @code-reviewer | clean-with-minors | 0 / 3 | 4/4 |
| 3 | TASK-TEST-001 | low | @code-reviewer | clean | 0 / 1 | 1/4 |
| 4 | TASK-DATA-001 | low | @code-reviewer | clean | 0 / 0 | 0/4 |
| 5 | TASK-PIN-001 | low | @code-reviewer | clean | 0 / 0 | 0/4 |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| @test-generator | 2 | Corpus dogfood that caught a real defect in a shipped report; history pin restructure |
| @code-reviewer | 0 (review) | Four adversarial rounds, every finding reproduced end-to-end against the live contract |
| (direct) | 5 | Addressing module, contract migration, boundary vocabulary, safety net, contract data |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `tools/spec-linter/spec_linter/sections.py` | ~190 | (direct) | ✅ | Addressing + opacity authority |
| `tools/spec-linter/tests/test_sections.py` | ~200 | (direct) | ✅ | 33 tests |
| `contracts/build_report.py` | +260 | (direct) | ✅ | Migration, vocabulary, duplicate rule, safety net |
| `tools/spec-linter/tests/test_build_report_contract.py` | +260 | (direct)/@test-generator | ✅ | Grid, duplicates, dogfood, FP guards |
| `WORKFLOW_CONTRACTS.yaml` + root pin | +25 | (direct) | ✅ | v3.18.0 addressing, v3.19.0 override |
| `docs/reviews/...-residuals-for-pr-b.md` | ~135 | (direct) | ✅ | R-1..R-5 handoff |

---

## Verification Results

### Lint Check

```text
shellcheck -S warning (make lint): clean, exit 0
```

**Status:** ✅ Pass

### Type Check

```text
N/A — no mypy gate configured; behavior covered by 328 unit tests
```

**Status:** ⏭️ Skipped

### Tests

```text
root suite:        183 passed
spec-linter suite: 334 passed (238 prior + 96 addressing/safety-net/override)
plugin build:      exit 0 (parity byte-identical, reviewer re-verified each round)
attack matrix:     18/18 addressing vectors blocked; clean report PASS, zero findings
archived corpus:   15/15 non-FAIL
```

**Status:** ✅ 517/517 Pass

---

## Review Verdict

> Whole-branch adversarial review — mandatory final step of the build
> (`WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`). Ship refuses
> `dirty` and `missing` verdicts.

| Attribute | Value |
|-----------|-------|
| **Verdict** | clean-with-minors |
| **Reviewer** | @code-reviewer |
| **Diff scope** | merge-base main..HEAD + working tree on feat/auto-exact-sections (both scopes: EXACT_SECTIONS and the maintainer's Codex adapters) |
| **Fix rounds used** | 4/2 (override: author=maintainer, rationale=live Critical bypass still open at round 2; budget raised explicitly rather than shipping a known hole) |

| # | Severity | Finding | Location | Resolution |
|---|----------|---------|----------|------------|
| 1 | Critical | My first draft's same-or-higher-level boundary let a stray `# ` line — or a `# TODO` inside a fenced snippet — truncate the section and hide an OPEN Critical | sections.py | fixed in fix-round-1: same-level boundary + fence opacity; both repros reproduced by me first, then pinned |
| 2 | Critical | ANY same-level heading truncated a scope (a plain `## Notes`, no trickery) — found by me while probing round 1 | sections.py | fixed in fix-round-2: closed boundary vocabulary; unrecognised heading is content |
| 3 | Critical | HTML comments were not an opaque region; fence run-length untracked (4-backtick nesting) | sections.py | fixed in fix-round-2: comments as second opaque region, CommonMark run-length rule |
| 4 | Critical | Duplicate monitoring covered 6 of 21 trusted boundary slugs, so 15 could truncate silently — including MOVED (no duplicate to find) | build_report.py | fixed in fix-round-3: monitored set == trust set; table-anchored safety net |
| 5 | Important | Safety net's row scan was fence-unaware, blocking a findings table quoted as an illustration | build_report.py | fixed in fix-round-4: `content_lines()` extracted and shared with heading detection |
| 6 | Important | A blank line splitting a legitimate table made its fragment read as findings (false FAIL) | build_report.py | fixed in fix-round-4: header inheritance (a split table is one table) |
| 7 | Important | Severity decoration evaded the exact-match predicate (`Critical (F1)` — my own report style) — found by me | build_report.py | fixed in fix-round-4: severity read as words; both directions pinned |
| 8 | Important | Inheritance reached across unrelated sections, so a headerless decision log inherited findings identity (false FAIL) | build_report.py | fixed in fix-round-4: inheritance scoped by column width |
| 9 | Minor | DESIGN decision log lagged the shipped mechanisms | DESIGN doc | fixed in fix-round-4: Decisions 5–8 recorded |
| 10 | Minor | R-1..R-5 table-grammar residuals remain | build_report.py | recorded — deferred to spec §7 / PR B by explicit maintainer scope decision; repros in `docs/reviews/2026-07-30-exact-sections-residuals-for-pr-b.md` |

Closing verdict: **clean-with-minors** — the reviewer could find no remaining way to hide an unresolved blocking finding through section-addressing manipulation; the open items fail in the safe direction or are table-grammar deferred to PR B.

---

## TDD Evidence (required when TDD Mode != off)

> TASK-MOD-001 and TASK-MIG-001 carry `tdd: required` in the manifest
> (medium risk, logic-bearing linter code) — effective mode `required`.

| # | Task ID | RED (failing first) | GREEN (passing after) |
|---|---------|---------------------|----------------------|
| 1 | TASK-MOD-001 | `pytest tests/test_sections.py` → ImportError (module absent), 14 tests written first | 14 passed after `sections.py` landed |
| 2 | TASK-MIG-001 | `pytest tests/test_build_report_contract.py` → 15 failed (§6.6 grid written first) | Full suite green after the migration |
| 3 | Fix rounds 1–4 | Each reviewer finding reproduced end-to-end against the live contract BEFORE fixing (documented per finding above) | 328 passed; 18/18 attack matrix |

Non-TDD tasks: contract data and the history pin (`tdd: off`, documental verification).

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Gate J crashed (AttributeError in judge.py, exit 1) — second consecutive run | VISIBLE SKIP; recorded as a follow-up for the maintainer | 0 |
| 2 | The branch carried two unrelated commits (Codex adapters, 73 files) from a parallel session | Surfaced to the maintainer, who chose to bundle; safety ref created; both scopes reviewed | +10m |
| 3 | A shipped archived report (`BUILD_REPORT_WORKFLOW_METRICS.md`) FAILed once severity decoration stopped hiding meaning | Real defect, not a false positive: resolution cell said "fixed across rounds 1–2", not the contract's `fixed in <ref>` grammar. Corpus swept (2 hits, 1 in a legacy report), cell corrected preserving its substance | +15m |
| 4 | Fix-loop budget (2) exhausted with a live Critical open | Maintainer explicitly raised the budget; rounds 3–4 are authorized, not a silent overrun | - |

---

## Autonomous Decisions

The build phase runs autonomously — it never pauses to ask the user. Every
decision fork reached during the build was resolved by choosing the safest
documented default. This section is the post-run review log: each row is a
fork the build resolved on its own. An empty table means the build hit zero
ambiguity (DESIGN fully pre-decided everything).

| # | Decision Point | Options Considered | Chose | Confidence | Rationale |
|---|----------------|--------------------|-------|------------|-----------|
| 1 | Boundary semantics | Standard Markdown (same-or-higher) vs conservative same-level | Same-level | 0.93 | A larger scope can add findings, never hide one |
| 2 | Safety-net anchoring | Every numbered row in the artifact vs findings-table structure | Table structure | 0.92 | Whole-row scanning broke a legitimate report (an "Important" decision cell); a gate that cries wolf gets routed around, which is its own security failure |
| 3 | Severity vocabulary | Normalize decoration only vs also block unknown words | Normalize only | 0.88 | Blocking unknown severities is a policy addition with real false-positive surface; PR B owns table-level vocabulary |
| 4 | Corpus defect | Correct the cell vs weaken the rule vs special-case the test | Correct the cell | 0.95 | The fact (resolved) was true; only the grammar was wrong |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Closed boundary vocabulary, opaque regions, duplicate monitoring across 21 slugs, and the table-anchored safety net — none in the original DESIGN | Four review rounds; each closed a reproduced Critical | Recorded as Decisions 5–8; scope grew beyond "exact matching + duplicates" but stayed inside §6's purpose |
| `docs/reviews/...-residuals-for-pr-b.md` created (not in the manifest) | Maintainer's scope decision needed a durable handoff | PR B's DEFINE consumes R-1..R-5 with repros |
| One archived report's resolution cell corrected | Issue #3 above | A shipped artifact now conforms; disclosed in the PR description |
| Authorized fix-round override grammar added (v3.19.0) — not in the manifest | The gate correctly refused this very report (4 rounds vs budget 2), and the contract had no way to express an authorized overrun; maintainer chose the override grammar over loosening the budget | Overruns stay attributed and auditable (WARN), the default budget stays 2 for everyone; 6 TDD tests |

---

## Blockers (if any)

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| None | - | - |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Decoy before | ✅ Pass | Named §3.1 repro test; reviewer reproduced pre-fix PASS at f5292fc and post-fix FAIL |
| AT-002 | Decoy after | ✅ Pass | Decoy inert as an address; findings table anywhere still blocks |
| AT-003 | Two exact sections | ✅ Pass | Duplicate FAIL with heading line numbers; union scan proven |
| AT-004 | Demoted heading | ✅ Pass | `L2.required_section` FAIL |
| AT-005 | Open Critical/Important | ✅ Pass | 18/18 vector matrix |
| AT-006 | Valid resolution | ✅ Pass | `fixed in <sha>` non-blocking |
| AT-007 | Invalid look-alike | ✅ Pass | Parametrized hedges still block |
| AT-008 | TDD heading set | ✅ Pass | Both spellings address; `TDD Evidence Notes` does not |
| AT-009 | Canonical + archived reports | ✅ Pass | 15/15 non-FAIL (after the disclosed correction) |
| AT-010 | Parity + history | ✅ Pass | build exit 0; 3.18.0→3.15.0 chain verified each round |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Addressing bypasses remaining | 0 | 0 (reviewer-confirmed after 4 rounds) | ✅ |
| False positives on legitimate reports | 0 | 0 (3 introduced during fix rounds, all closed) | ✅ |

---

## Workflow Metrics

> Machine-readable run metrics (`WORKFLOW_CONTRACTS.yaml` → `workflow_metrics`,
> schema v1). Values are MEASURED or `{value: null, reason: "..."}` — never
> estimated, interpolated, or copied from a prior run. Ship summarizes this
> block into SHIPPED; it never auto-changes any policy.

```yaml
workflow_metrics:
  schema_version: 1
  feature: "EXACT_SECTIONS"
  phase_duration_seconds: { value: null, reason: "interactive session carries no wall-clock instrumentation" }
  time_to_first_green_seconds: { value: null, reason: "not instrumented" }
  task_count: 5
  effective_parallelism: 1
  tests_by_type: { unit: 96, contract: 1, documental: 0, integration: 0 }
  reopened_tasks: 2
  fix_rounds: { local: 0, final: 4 }
  findings: { critical: 4, important: 4, minor: 2, by_stage: { task_review: 0, branch_review: 10 } }
  requirements: { must_total: 6, must_verified: 6, excepted: 0 }
  operational_skips: ["J:crash-exit1"]
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

**If Complete:** `/ship .claude/sdd/features/DEFINE_EXACT_SECTIONS.md`
