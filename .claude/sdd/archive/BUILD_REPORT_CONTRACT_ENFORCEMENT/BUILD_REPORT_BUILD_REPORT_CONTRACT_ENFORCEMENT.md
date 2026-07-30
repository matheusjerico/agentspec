# BUILD REPORT: Build Report Contract Enforcement

> Implementation report for BUILD_REPORT_CONTRACT_ENFORCEMENT

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_REPORT_CONTRACT_ENFORCEMENT |
| **Date** | 2026-07-29 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_BUILD_REPORT_CONTRACT_ENFORCEMENT.md](../features/DEFINE_BUILD_REPORT_CONTRACT_ENFORCEMENT.md) |
| **DESIGN** | [DESIGN_BUILD_REPORT_CONTRACT_ENFORCEMENT.md](../features/DESIGN_BUILD_REPORT_CONTRACT_ENFORCEMENT.md) |
| **Status** | ✅ Shipped |
| **Schema Version** | 2 |
| **TDD Mode** | off |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 13/13 |
| **Files Created** | 3 (+10 modified) |
| **Lines of Code** | ~1,400 added (883 in new files, ~513 across modified) |
| **Build Time** | ~2h interactive (incl. 2 review fix rounds) |
| **Tests Passing** | 149/149 (87 root + 62 spec-linter) |
| **Agents Used** | 4 specialists + (direct) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | WORKFLOW_CONTRACTS.yaml: build contract + binding flip + v3.8.0 | (direct) | ✅ Complete | - | YAML verified parseable; `off` quoted vs YAML 1.1 boolean trap |
| 2 | contracts/build_report.py (BuildReportContract) | @python-developer | ✅ Complete | - | 9 rule ids; legacy short-circuit; frozen slotted dataclass |
| 3 | cli.py: --legacy-mode + build routing | @python-developer | ✅ Complete | - | Exit-code contract unchanged; precise operational errors |
| 4 | tests/test_build_report_contract.py | @test-generator | ✅ Complete | - | 16 initial + 6 fix-round regression tests (22 final) |
| 5 | tests/test_cli.py build-phase additions | @test-generator | ✅ Complete | - | 6 CLI tests incl. legacy modes + argparse exit 2 |
| 6 | BUILD_REPORT_TEMPLATE.md metadata rows | (direct) | ✅ Complete | - | Schema Version + TDD Mode; checklist item |
| 7 | sdd-build SKILL.md Step 6.5 Contract Gate | (direct) | ✅ Complete | - | Mirrors sdd-define/sdd-design gate text |
| 8 | sdd-ship SKILL.md re-validation | (direct) | ✅ Complete | - | + checklist-item tie-in after review finding 3 |
| 9 | sdd-autopilot SKILL.md Gate L/S wiring | (direct) | ✅ Complete | - | `--legacy-mode fail`; Gate S "all 6 items" |
| 10 | tests/test_build_quality_gates.py anchors | @test-generator | ✅ Complete | - | 9 new documental tests; 2 updated for 6-item checklist |
| 11 | tests/test_plugin_parity.py | @test-generator | ✅ Complete | - | 19 tests; both-sides normalization fix (see Issues #1) |
| 12 | build-plugin.sh Step 0 ignore + Step 5e parity | @shell-script-specialist | ✅ Complete | - | shellcheck -S warning clean |
| 13 | USAGE.md build-phase documentation | (direct) | ✅ Complete | - | Build-report linting mode + --legacy-mode |

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Agent Key:**
- `@{agent-name}` = Delegated to specialist agent via Task tool
- `(direct)` = Built directly by build-agent (no specialist matched)

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| @python-developer | 2 | Contract protocol conformance, frozen/slotted dataclasses, regex parsing, exit-code discipline |
| @test-generator | 4 | pytest fixture+mutator pattern, parametrized failure paths, documental anchors, parity normalization |
| @shell-script-specialist | 1 | build-plugin.sh step idioms, shellcheck-clean guards |
| @code-reviewer | 0 (review) | Whole-branch adversarial review + 2 scoped fix-round re-reviews |
| (direct) | 6 | DESIGN patterns + WORKFLOW_CONTRACTS conventions for policy/markdown/YAML edits |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `tools/spec-linter/spec_linter/contracts/build_report.py` | 401 | @python-developer | ✅ | New contract class (created; +fix rounds) |
| `tools/spec-linter/tests/test_build_report_contract.py` | 318 | @test-generator | ✅ | 22 rule tests |
| `tests/test_plugin_parity.py` | 164 | @test-generator | ✅ | 19 parity tests |
| `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | +45/-11 | (direct) | ✅ | Modified — v3.8.0 |
| `tools/spec-linter/spec_linter/cli.py` | +108/-7 | @python-developer | ✅ | Modified |
| `tools/spec-linter/tests/test_cli.py` | +174 | @test-generator | ✅ | Modified (append-only) |
| `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | +6/-1 | (direct) | ✅ | Modified |
| `.claude/skills/sdd-build/SKILL.md` | +39/-1 | (direct) | ✅ | Modified |
| `.claude/skills/sdd-ship/SKILL.md` | +16/-0 | (direct) | ✅ | Modified |
| `.claude/skills/sdd-autopilot/SKILL.md` | +6/-4 | (direct) | ✅ | Modified |
| `tests/test_build_quality_gates.py` | +77/-9 | @test-generator | ✅ | Modified |
| `build-plugin.sh` | +26/-1 | @shell-script-specialist | ✅ | Modified |
| `tools/spec-linter/USAGE.md` | +16/-0 | (direct) | ✅ | Modified |

---

## Verification Results

### Lint Check

```text
shellcheck -S warning (make lint): clean, exit 0
spec-lint --phase design on DESIGN doc: PASS (regression check of untouched phases)
```

**Status:** ✅ Pass

### Type Check

```text
N/A — repo has no mypy configuration; type hints follow existing spec_linter conventions
```

**Status:** ⏭️ Skipped

### Tests

```text
root suite:        python3 -m pytest tests/ -q          → 87 passed (incl. 19 parity)
spec-linter suite: python3 -m pytest tests/ -q          → 62 passed
plugin build:      ./build-plugin.sh                    → exit 0 (Step 0 tests + Step 5e parity green)
```

| Test | Result |
|------|--------|
| `tests/test_build_quality_gates.py` (17: 8 pre-existing + 9 new) | ✅ Pass |
| `tests/test_plugin_parity.py` (19) | ✅ Pass |
| `tools/spec-linter/tests/test_build_report_contract.py` (22) | ✅ Pass |
| `tools/spec-linter/tests/test_cli.py` (14 + 6 new) | ✅ Pass |
| Remaining root + linter suites (regressions) | ✅ Pass |

**Status:** ✅ 149/149 Pass

---

## Review Verdict

> Whole-branch adversarial review — mandatory final step of the build
> (`WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`). Ship refuses
> `dirty` and `missing` verdicts.

| Attribute | Value |
|-----------|-------|
| **Verdict** | clean-with-minors |
| **Reviewer** | @code-reviewer |
| **Diff scope** | uncommitted working tree on `main` (no merge-base; full-manifest + working-tree diff review) |
| **Fix rounds used** | 2/2 |

| # | Severity | Finding | Location | Resolution |
|---|----------|---------|----------|------------|
| 1 | Critical | Open-finding detection was a single `\bopen\b` word — unresolved wording ("Not resolved — deferred") passed as PASS | build_report.py | fixed in round 1+2 (working tree): template-shaped `_RESOLVED` pattern (fixed/resolved in ref); regression tests for all hedge strings |
| 2 | Critical | Findings scan unscoped to the Review Verdict table — Autonomous Decisions rows false-positived | build_report.py | fixed in round 1 (working tree): scan scoped via `_section_after("review_verdict")` |
| 3 | Important | Ship re-validation prose-only; not in `pre_ship_checklist`/Gate S; no `--legacy-mode` at ship time | WORKFLOW_CONTRACTS.yaml, sdd-ship, sdd-autopilot | fixed in round 1 (working tree): 6th checklist item `build_report_contract_gate_pass`; Gate S "all 6 items" + `--legacy-mode fail` |
| 4 | Minor | Schema Version value never compared (presence-only) | build_report.py | fixed in round 1: `BR.schema_version` FAIL on mismatch |
| 5 | Minor | Unfilled `### Overall: {...}` placeholder silently skipped completeness check | build_report.py | fixed in round 1: placeholder → `BR.tasks_incomplete` FAIL |
| 6 | Minor | `--legacy-mode` warn/fail names hardcoded to manual/autopilot context keys | cli.py | recorded (minor) — accepted per DESIGN Decision 3: the flag names the consumer context; contract owns severity |
| 7 | Critical (round-1 re-review, C1) | Heading-level mismatch: `### Review Verdict` satisfied presence but emptied the scan scope | build_report.py | fixed in round 2 (working tree): single `##`-level heading vocabulary for presence AND scoping; demotion now `L2.required_section` FAIL |
| 8 | Important (round-1 re-review, E1) | Prefix match accepted verb-prefixed hedges ("Fixed - actually not") | build_report.py | fixed in round 2 (working tree): template-shaped `_RESOLVED` pattern; parametrized regression test |
| 9 | Minor | Interposed benign `##` heading inside Review Verdict can still truncate the findings scan | build_report.py | recorded (minor) — known limitation: requires active structural deviation from the template; a deterministic linter cannot defeat a deliberately deceptive report author (they could omit the row entirely); documented here rather than hidden |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Parity test false positive: canonical WORKFLOW_CONTRACTS.yaml legitimately contains a `${CLAUDE_PLUGIN_ROOT}/agents/` literal (agent_resolution comment); one-sided normalization corrupted the identical line | Compare canonical forms of BOTH sides (`normalize(plugin) == normalize(canonical)`) | +10m |
| 2 | rtk PreToolUse hook rewrites `python3 -m pytest` to a bare `pytest` spawn not on PATH | Invoke via `rtk proxy python3 -m pytest ...` throughout | +5m |
| 3 | Round-1 fix for finding 1 used a word-boundary match — the new regression test itself caught that "Not resolved" contains "resolved" | Tightened to prefix in round 1, then template-shaped form in round 2 | +10m |
| 4 | Dogfood catch: this report's own Step 6.5 gate FAILed on first run — a raw pipe inside a code span in finding row 1 split the table cell, so its resolution no longer parsed as template-shaped | Reworded the cell without the raw pipe; re-lint → PASS (exit 0, both legacy modes) | +5m |

---

## Autonomous Decisions

The build phase runs autonomously — it never pauses to ask the user. Every
decision fork reached during the build was resolved by choosing the safest
documented default. This section is the post-run review log: each row is a
fork the build resolved on its own. An empty table means the build hit zero
ambiguity (DESIGN fully pre-decided everything).

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Legacy report rule scope | Run all v2 rules on legacy reports vs legacy short-circuit | Short-circuit: only `BR.legacy_report` + fail-closed dirty/missing verdict check | AT-008 requires WARN (not FAIL) for legacy manual runs; old reports lack v2 sections and would always FAIL otherwise; dirty/missing stays fail-closed per plan §17.2 |
| 2 | Resolution-cell semantics for blocking findings | Word match / prefix match / template-shaped `fixed\|resolved in <ref>` | Template-shaped (strictest) | Fail-closed: hedged wording ("Fixed - actually not") must block; template vocabulary is "fixed in {sha}" |
| 3 | Ship-side wiring depth (review finding 3) | Prose-only in sdd-ship vs 6th `pre_ship_checklist` item + Gate S update | 6th checklist item + Gate S "all 6 items" + documental test updates | DEFINE MUST: "same reasons refuse Ship"; checklist is what Gate S actually consumes — prose alone left /auto unenforced |
| 4 | Schema-version mismatch rule | Fold into `BR.legacy_report` vs new rule id | New `BR.schema_version` (9th rule, beyond DESIGN's 8) | An explicit wrong version is not "pre-contract"; distinct rule id keeps the finding diagnosable |
| 5 | Section heading strictness | Any-level headings for presence vs `##`-only vocabulary | `##`-only for both presence and scoping | Reviewer's option (b): the two checks can never disagree; demoted headings fail closed |
| 6 | `ship.pre_ship_checklist` growth breaks 2 shipped documental tests | Preserve old tests vs update anchors | Updated `test_pre_ship_checklist_*` and `test_autopilot_has_gate_r` to the 6-item contract | Documental tests are drift guards; the drift is intentional, versioned (3.8.0), and review-driven |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| 9 `BR.*`/section rule ids instead of the designed 8 (added `BR.schema_version`) | Review finding 4 (schema version value never compared) | Additive; documented in USAGE-level behavior via rule output |
| `ship.pre_ship_checklist` extended to 6 items + Gate S row updated (DESIGN scoped ship changes to skill prose) | Review finding 3 — prose alone left Autopilot's Gate S unenforced | 2 documental tests updated; version history amended |
| Parity test normalizes both sides instead of plugin-side only | Canonical files may legitimately contain plugin-form literals (Issue #1) | Comparison still catches content drift (self-tests prove it) |

---

## Blockers (if any)

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| None | - | - |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Valid report → PASS/exit 0 | ✅ Pass | `test_valid_report_passes`, CLI valid-report exit-0 test; this report's own Step 6.5 gate below |
| AT-002 | Dirty verdict → FAIL/exit 1 | ✅ Pass | `test_verdict_dirty_fails`, CLI dirty exit-1 test |
| AT-003 | Missing verdict section → FAIL | ✅ Pass | `test_verdict_row_missing_fails`, `test_review_verdict_section_missing_is_required_section_fail` |
| AT-004 | Open Critical/Important finding → FAIL | ✅ Pass | injected-Critical-OPEN test + `test_unresolved_wording_blocks_even_without_open_word` + `test_verb_prefixed_hedge_still_blocks` |
| AT-005 | Fix-round budget breach → FAIL | ✅ Pass | exceeded (3/2) and budget-divergence (0/3) tests |
| AT-006 | TDD-mandatory without evidence → FAIL | ✅ Pass | TDD-evidence missing/present pair |
| AT-007 | Incomplete tasks + COMPLETE status → FAIL | ✅ Pass | tasks-incomplete pair + placeholder-Overall regression test |
| AT-008 | Legacy report, manual mode → WARN, proceeds | ✅ Pass | legacy WARN unit test + CLI legacy default exit-0 test |
| AT-009 | Legacy report, Autopilot → blocks | ✅ Pass | legacy FAIL unit test + CLI `--legacy-mode fail` exit-1 test + documental anchor `test_autopilot_lints_build_report_fail_closed` |
| AT-010 | Plugin parity divergence detected | ✅ Pass | `test_plugin_parity.py` self-tests + live catch: Step 5e failed on a real normalizer defect during this build, fixed and re-proven green |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Existing-suite regressions | 0 | 0 (87 root + 62 linter green) | ✅ |
| New rule-family coverage | ≥1 PASS + ≥1 FAIL path each (≥10 tests) | 22 rule tests + 6 CLI tests | ✅ |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Review Verdict is clean or clean-with-minors
- [x] Contract gate passed: `spec-lint --phase build` exit 0 (sdd-build Step 6.5)
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_BUILD_REPORT_CONTRACT_ENFORCEMENT.md`
