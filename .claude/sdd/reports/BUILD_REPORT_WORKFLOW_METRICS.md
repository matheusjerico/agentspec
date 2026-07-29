# BUILD REPORT: Workflow Metrics

> Implementation report for WORKFLOW_METRICS

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | WORKFLOW_METRICS |
| **Date** | 2026-07-29 |
| **Author** | build-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_WORKFLOW_METRICS.md](../features/DEFINE_WORKFLOW_METRICS.md) |
| **DESIGN** | [DESIGN_WORKFLOW_METRICS.md](../features/DESIGN_WORKFLOW_METRICS.md) |
| **Status** | Complete |
| **Schema Version** | 2 |
| **TDD Mode** | required |
| **Risk Level** | medium (echo from DEFINE) |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 6/6 (v2 manifest) |
| **Files Created** | 2 new + 6 modified (SHIPPED_TEMPLATE.md added by review F4) |
| **Lines of Code** | ~400 added |
| **Tests Passing** | 365/365 (172 root + 193 spec-linter) |
| **Agents Used** | 2 specialists + (direct) |

---

## Task Execution with Agent Attribution

| # | Task ID | Task | Agent | Status | Commit | Duration | Notes |
|---|---------|------|-------|--------|--------|----------|-------|
| 1 | TASK-CONTRACT-001 | workflow_metrics block + v3.16.0 | (direct) | ✅ Complete | session | - | 13-key closed catalog; history entry re-landed after a silent-replace slip |
| 2 | TASK-TMPL-001 | Report template Workflow Metrics section | (direct) | ✅ Complete | session | - | Fenced yaml skeleton, all 13 keys |
| 3 | TASK-LINT-001 | 5 BR.metrics rules — TDD | (direct) | ✅ Complete | session | - | RED first (17 failed) → GREEN; +4 regression tests in fix rounds |
| 4 | TASK-SKILL-001 | sdd-build emission conduct | (direct) | ✅ Complete | session | - | + brace-guard disclosure (review) |
| 5 | TASK-SKILL-002 | sdd-ship summary + boundary | (direct) | ✅ Complete | session | - | + SHIPPED_TEMPLATE landing spot (review F4) |
| 6 | TASK-TEST-001 | Documental anchors | @test-generator | ✅ Complete | session | - | 10 tests incl. AT-009 comparability |

**Manifest:** v2 — tasks consumed from the DESIGN Task Manifest (topological order, no inference)

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Agent Key:**
- `@{agent-name}` = Delegated to specialist agent via Task tool
- `(direct)` = Built directly by build-agent (no specialist matched)

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |
|---|-----|----------|-------|-------|-------------------|--------|--------|
| 1 | REQ-001 | MUST | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | contract | Pass | clean-with-minors |
| 2 | REQ-002 | MUST | TASK-TMPL-001 | tests/test_workflow_metrics.py | deterministic_inspection | Pass | clean |
| 3 | REQ-003 | MUST | TASK-SKILL-001 | tests/test_workflow_metrics.py | deterministic_inspection | Pass | clean-with-minors |
| 4 | REQ-004 | MUST | TASK-SKILL-002 | tests/test_workflow_metrics.py | deterministic_inspection | Pass | clean-with-minors |
| 5 | REQ-005 | MUST | TASK-LINT-001 | tools/spec-linter/tests/test_metrics_rules.py | unit | Pass | clean-with-minors |
| 6 | REQ-006 | MUST | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | contract | Pass | clean |
| 7 | REQ-007 | SHOULD | TASK-LINT-001, TASK-TEST-001 | tools/spec-linter/tests/test_metrics_rules.py, tests/test_workflow_metrics.py | unit | Pass | clean |
| 8 | REQ-008 | COULD | TASK-CONTRACT-001 | tests/test_workflow_metrics.py | deterministic_inspection | Pass | clean |

---

## Task Reviews

| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |
|---|---------|------|----------|---------|----------------------|------------|
| 1 | TASK-CONTRACT-001 | medium | @code-reviewer | clean-with-minors | 0 / 1 | 1/1 |
| 2 | TASK-TMPL-001 | low | @code-reviewer | clean | 0 / 0 | 0/1 |
| 3 | TASK-LINT-001 | medium | @code-reviewer | clean-with-minors | 0 / 2 | 1/1 |
| 4 | TASK-SKILL-001 | medium | @code-reviewer | clean-with-minors | 0 / 1 | 1/1 |
| 5 | TASK-SKILL-002 | low | @code-reviewer | clean-with-minors | 0 / 1 | 1/1 |
| 6 | TASK-TEST-001 | low | @code-reviewer | clean | 0 / 0 | 0/1 |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| @test-generator | 1 | Documental anchors incl. the AT-009 two-block comparability pin |
| @code-reviewer | 0 (review) | Whole-branch adversarial review, 2 verification rounds with independent repros |
| (direct) | 7 | Contract data, templates, linter rules (TDD), skills |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `tools/spec-linter/tests/test_metrics_rules.py` | ~290 | (direct) | ✅ | 21 tests, RED-first |
| `tests/test_workflow_metrics.py` | ~130 | @test-generator | ✅ | 10 documental |
| `WORKFLOW_CONTRACTS.yaml` | +45 | (direct) | ✅ | v3.16.0 |
| `build_report.py` + `cli.py` | +170 | (direct) | ✅ | 5 rules + wiring |
| `BUILD_REPORT_TEMPLATE.md` / `SHIPPED_TEMPLATE.md` | +45 | (direct) | ✅ | Emission skeleton + summary landing spot |
| `sdd-build / sdd-ship SKILL.md` | +30 | (direct) | ✅ | Conduct + boundary |

---

## Verification Results

### Lint Check

```text
shellcheck -S warning (make lint): clean, exit 0
```

**Status:** ✅ Pass

### Type Check

```text
N/A — spec-linter has no mypy gate configured; rules covered by 21 unit tests
```

**Status:** ⏭️ Skipped

### Tests

```text
root suite:        172 passed (162 prior + 10 documental)
spec-linter suite: 193 passed (172 prior + 21 metrics rules)
plugin build:      exit 0 (Step 5e parity green; reviewer re-verified byte-identity)
```

**Status:** ✅ 365/365 Pass

---

## Review Verdict

> Whole-branch adversarial review — mandatory final step of the build
> (`WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`). Ship refuses
> `dirty` and `missing` verdicts.

| Attribute | Value |
|-----------|-------|
| **Verdict** | clean-with-minors |
| **Reviewer** | @code-reviewer |
| **Diff scope** | merge-base main..HEAD + working tree on feat/auto-workflow-metrics |
| **Fix rounds used** | 2/2 |

| # | Severity | Finding | Location | Resolution |
|---|----------|---------|----------|------------|
| 1 | Critical (F1) | A verbatim unfilled template skeleton PASSed the anti-fabrication rule (no placeholder guard) | build_report.py | fixed in fix-round-1: brace guard on measured strings AND reasons; 2 regression tests; reviewer re-ran the original repro → FAIL |
| 2 | Important (F2) | `path.endswith("reason")` exempted any `*reason`-named key from the estimate scan | build_report.py | fixed in fix-round-1: exemption now shape-aware (availability branch only); regression test |
| 3 | Important (F3) | Extra keys rode the availability mapping unscanned | build_report.py | fixed in fix-round-1: mapping closed to {value, reason}; regression test |
| 4 | Important (F4) | sdd-ship summary step contradicted "do not improvise sections" — SHIPPED_TEMPLATE had no landing spot | sdd-ship + SHIPPED_TEMPLATE | fixed in fix-round-1: Workflow Metrics subsection added under Metrics; skill points at it by name (manifest deviation, recorded below) |
| 5 | Important (F5) | DESIGN cited a phantom `build.report_contract.metrics` wiring key (4 places) | DESIGN doc | fixed across rounds 1–2: all citations rewritten to the real top-level arming; repo-wide grep 0 hits |
| 6 | Minor (F6) | DESIGN claimed linter code is not shipped in the plugin (false) | DESIGN doc | fixed in fix-round-1: corrected to plugin/tools/spec-linter + parity test |
| 7 | Minor (F7) | Redundant `metrics_parse_broken` precedence flag | build_report.py | fixed in fix-round-1: field removed, comment explains fence-present+None |
| 8 | Minor | Brace guard rejects legitimate strings containing literal braces (fails safe) | build_report.py | recorded (accepted trade-off, mirrors existing matrix/overall guards) — disclosed in the module docstring and sdd-build emission guidance |

Closing verdict: **clean-with-minors** — all F1–F7 verified resolved by independent repro; the disclosed fails-safe brace trade-off is the only residual.

---

## TDD Evidence (required when TDD Mode != off)

> TASK-LINT-001 carries `tdd: required` in the manifest (medium risk,
> logic-bearing linter code) — the effective mode for this build is `required`.

| # | Task ID | RED (failing first) | GREEN (passing after) |
|---|---------|---------------------|----------------------|
| 1 | TASK-LINT-001 | `pytest tests/test_metrics_rules.py` → 17 failed (TypeError: unexpected keyword 'metrics_config' — rules not implemented) | Same command → 17 passed after implementing the 5 rules + wiring |
| 2 | TASK-LINT-001 (fix rounds) | 4 review-driven regression tests written against the reported repros (placeholder, sibling-reason, closed mapping) | 21 passed; full suite 193 |

Non-TDD tasks: contract data, templates, and skill prose (TASK-CONTRACT-001,
TASK-TMPL-001, TASK-SKILL-001/002 — `tdd: off` in the manifest, documental
verification); TASK-TEST-001 is itself the test artifact.

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Gate J unavailable (exit 3, daily budget) | VISIBLE SKIP | 0 |
| 2 | version_history edit silently no-op'd via str.replace, leaving 3.16.0 header on the 3.15.0 body | Re-landed with an exact-match Edit; documental test now pins the entry | +5m |
| 3 | Template-block test helper stripped braces from yaml flow mappings | Placeholder regex narrowed to brace tokens without colons | +3m |

---

## Autonomous Decisions

The build phase runs autonomously — it never pauses to ask the user. Every
decision fork reached during the build was resolved by choosing the safest
documented default. This section is the post-run review log: each row is a
fork the build resolved on its own. An empty table means the build hit zero
ambiguity (DESIGN fully pre-decided everything).

| # | Decision Point | Options Considered | Chose | Confidence | Rationale |
|---|----------------|--------------------|-------|------------|-----------|
| 1 | F4 fix direction | Extend SHIPPED_TEMPLATE vs reword sdd-ship to reuse the fixed Metrics rows | Extend the template (dedicated subsection) | 0.90 | The fixed rows can't hold per-run metric shapes; a named landing spot keeps "no improvised sections" true |
| 2 | Brace false-positive | Fix with an escape grammar vs disclose as fails-safe trade-off | Disclose (docstring + emission guidance) | 0.88 | Mirrors the existing matrix/overall guards; rejects-valid is the safe failure direction; escape grammar is complexity without a driving case |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `SHIPPED_TEMPLATE.md` modified (not in the 8-file manifest) | Review F4 — the ship summary needed a template landing spot | SHIPPED docs gain a Workflow Metrics subsection; archived pre-Inc-9 SHIPPED docs are unaffected (nothing lints them) |
| Placeholder guard + closed availability mapping (not in DESIGN) | Review F1/F3 | The anti-fabrication rule actually resists the template-copy attack |

---

## Blockers (if any)

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| None | - | - |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Contract registered | ✅ Pass | block test: schema_version 1, 13-key catalog, availability rule, behavior |
| AT-002 | Template shape | ✅ Pass | full-catalog + availability-mapping template tests |
| AT-003 | Valid block passes | ✅ Pass | unit: valid fixture → exit-0-equivalent PASS, zero metrics findings |
| AT-004 | Fabrication rejected | ✅ Pass | unit: bare null, tilde null, null-no-reason, empty reason, estimate markers, placeholders — all FAIL naming the key |
| AT-005 | Schema versioned | ✅ Pass | unit: version mismatch FAIL |
| AT-006 | Legacy path | ✅ Pass | unit: absent block → WARN (warn) / FAIL (fail); legacy report skips rules |
| AT-007 | Build conduct | ✅ Pass | documental: measured-only, forbidden verbs, brace guidance |
| AT-008 | Ship conduct | ✅ Pass | documental: summary landing spot + §15.3 boundary verbatim |
| AT-009 | Comparability | ✅ Pass | test_two_same_version_blocks_compare_without_prose |
| AT-010 | Parity + prior anchors | ✅ Pass | build exit 0; 172 root incl. all prior increments' tests |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Regressions | 0 | 0 | ✅ |
| Catalog↔template parity | 13/13 keys | Pinned by test + reviewer | ✅ |

---

## Workflow Metrics

> Machine-readable run metrics (`WORKFLOW_CONTRACTS.yaml` → `workflow_metrics`,
> schema v1). Values are MEASURED or `{value: null, reason: "..."}` — never
> estimated, interpolated, or copied from a prior run. Ship summarizes this
> block into SHIPPED; it never auto-changes any policy.

```yaml
workflow_metrics:
  schema_version: 1
  feature: "WORKFLOW_METRICS"
  phase_duration_seconds: { value: null, reason: "interactive session carries no wall-clock instrumentation" }
  time_to_first_green_seconds: { value: null, reason: "not instrumented; first GREEN followed the RED run within the same session" }
  task_count: 6
  effective_parallelism: 1
  tests_by_type: { unit: 21, contract: 0, documental: 10, integration: 0 }
  reopened_tasks: 0
  fix_rounds: { local: 0, final: 2 }
  findings: { critical: 1, important: 4, minor: 3, by_stage: { task_review: 0, branch_review: 8 } }
  requirements: { must_total: 6, must_verified: 6, excepted: 0 }
  operational_skips: ["J:exit3"]
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

**If Complete:** `/ship .claude/sdd/features/DEFINE_WORKFLOW_METRICS.md`
