"""Tests for BuildReportContract, run through `engine.lint`.

One test per documented BR.* rule family (PASS + FAIL, plus a legacy fork),
built on a single module-level VALID_REPORT fixture — a minimal but fully
conformant schema-v2 build report — mutated per test via the `mutate` helper
so each test's intent (what changed, what should break) stays legible.
"""

from __future__ import annotations

from spec_linter.contracts.build_report import BuildReportContract
from spec_linter.engine import lint
from spec_linter.verdict import Level, Verdict

REQUIRED_SECTIONS = [
    "metadata",
    "summary",
    "task_execution_with_agent_attribution",
    "files_created",
    "verification_results",
    "review_verdict",
    "acceptance_test_verification",
    "final_status",
]
VERDICTS = ["clean", "clean-with-minors", "dirty", "missing"]
FIX_BUDGET = 2
SCHEMA_VERSION = 2
TDD_MODE_VALUES = ["off", "opt-in", "required"]


def _contract(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
    )


def _lint(report: str, legacy_level: Level = Level.WARN) -> Verdict:
    return lint(report, _contract(legacy_level))


def _rules(verdict: Verdict) -> list[str]:
    return [f.rule for f in verdict.findings]


def mutate(report: str, old: str, new: str) -> str:
    """Replace `old` with `new`, asserting `old` is actually present in
    `report` — a guard against silently-green fixtures if VALID_REPORT
    drifts and a mutation stops mutating anything."""
    assert old in report, f"fixture drift: {old!r} not found in report"
    return report.replace(old, new)


VALID_REPORT = """\
# BUILD REPORT: SAMPLE_FEATURE

## Metadata

| Field | Value |
|-------|-------|
| **Feature** | SAMPLE_FEATURE |
| **Schema Version** | 2 |
| **TDD Mode** | off |
| **Date** | 2026-07-29 |

## Summary

Implemented the sample feature end-to-end per DESIGN_SAMPLE_FEATURE.md.

## Task Execution with Agent Attribution

| # | Task | Agent | Status |
|---|------|-------|--------|
| 1 | Implement parser | python-pro | ✅ |
| 2 | Write tests | test-generator | ✅ |

## Files Created

- `src/sample/parser.py`
- `tests/test_parser.py`

## Verification Results

- `pytest tests/` - 12 passed
- `ruff check .` - 0 violations

## Review Verdict

| Field | Value |
|-------|-------|
| **Verdict** | clean |
| **Fix rounds used** | 0/2 |

| # | Severity | Description | Location | Resolution |
|---|----------|--------------|----------|------------|
| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |

## Acceptance Test Verification

| Acceptance Test | Status |
|------------------|--------|
| Parses valid input | ✅ Verified |
| Rejects malformed input | ✅ Verified |

## Final Status

| **Tasks Completed** | 2/2 |

### Overall: ✅ COMPLETE
"""


def test_valid_report_passes() -> None:
    verdict = _lint(VALID_REPORT)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_verdict_dirty_fails() -> None:
    report = mutate(VALID_REPORT, "| **Verdict** | clean |", "| **Verdict** | dirty |")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.review_verdict_dirty" in _rules(verdict)


def test_verdict_invalid_value_fails() -> None:
    report = mutate(VALID_REPORT, "| **Verdict** | clean |", "| **Verdict** | banana |")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    rules = _rules(verdict)
    assert "BR.review_verdict_value" in rules
    assert "BR.review_verdict_dirty" not in rules


def test_verdict_row_missing_fails() -> None:
    report = mutate(VALID_REPORT, "| **Verdict** | clean |\n", "")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.review_verdict_missing" in _rules(verdict)


def test_review_verdict_section_missing_is_required_section_fail() -> None:
    start = VALID_REPORT.index("## Review Verdict")
    end = VALID_REPORT.index("## Acceptance Test Verification")
    section = VALID_REPORT[start:end]
    report = mutate(VALID_REPORT, section, "")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    section_findings = [f for f in verdict.findings if f.rule == "L2.required_section"]
    assert any(f.field == "review_verdict" for f in section_findings)


def test_open_blocking_finding_fails() -> None:
    old = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
    new = old + "\n| 2 | Critical | injected bug | file.py:1 | OPEN |"
    report = mutate(VALID_REPORT, old, new)
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_minor_open_finding_does_not_block() -> None:
    old = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
    new = old + "\n| 2 | Minor | cosmetic nit | file.py:1 | OPEN |"
    report = mutate(VALID_REPORT, old, new)
    verdict = _lint(report)
    assert "BR.open_blocking_finding" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_fix_rounds_exceeded_fails() -> None:
    report = mutate(
        VALID_REPORT, "| **Fix rounds used** | 0/2 |", "| **Fix rounds used** | 3/2 |"
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.fix_rounds_budget" in _rules(verdict)


def test_fix_rounds_budget_diverges_from_contract_fails() -> None:
    report = mutate(
        VALID_REPORT, "| **Fix rounds used** | 0/2 |", "| **Fix rounds used** | 0/3 |"
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.fix_rounds_budget" in _rules(verdict)


def test_tdd_mode_optin_without_evidence_section_fails() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | opt-in |")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.tdd_evidence_missing" in _rules(verdict)


def test_tdd_mode_optin_with_evidence_section_passes() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | opt-in |")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | RED | GREEN |\n"
        "|------|-----|-------|\n"
        "| Implement parser | test_parser_rejects_bad_input fails | "
        "test_parser_rejects_bad_input passes |\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_tasks_incomplete_fails_when_overall_marked_complete() -> None:
    report = mutate(
        VALID_REPORT,
        "| 1 | Implement parser | python-pro | ✅ |",
        "| 1 | Implement parser | python-pro | ⏳ |",
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.tasks_incomplete" in _rules(verdict)


def test_tasks_incomplete_does_not_fire_when_overall_in_progress() -> None:
    report = mutate(
        VALID_REPORT,
        "| 1 | Implement parser | python-pro | ✅ |",
        "| 1 | Implement parser | python-pro | ⏳ |",
    )
    report = mutate(report, "### Overall: ✅ COMPLETE", "### Overall: 🔄 IN PROGRESS")
    verdict = _lint(report)
    assert "BR.tasks_incomplete" not in _rules(verdict)


def test_legacy_report_without_schema_version_is_warn_at_manual_level() -> None:
    report = mutate(VALID_REPORT, "| **Schema Version** | 2 |\n", "")
    verdict = _lint(report, legacy_level=Level.WARN)
    assert verdict.level == Level.WARN
    assert len(verdict.findings) == 1
    assert verdict.findings[0].rule == "BR.legacy_report"


def test_legacy_report_without_schema_version_is_fail_at_autopilot_level() -> None:
    report = mutate(VALID_REPORT, "| **Schema Version** | 2 |\n", "")
    verdict = _lint(report, legacy_level=Level.FAIL)
    assert verdict.level == Level.FAIL
    assert len(verdict.findings) == 1
    assert verdict.findings[0].rule == "BR.legacy_report"


def test_legacy_report_with_dirty_verdict_fails_closed_even_at_warn_level() -> None:
    report = mutate(VALID_REPORT, "| **Schema Version** | 2 |\n", "")
    report = mutate(report, "| **Verdict** | clean |", "| **Verdict** | dirty |")
    verdict = _lint(report, legacy_level=Level.WARN)
    assert verdict.level == Level.FAIL
    assert "BR.review_verdict_dirty" in _rules(verdict)


def test_unresolved_wording_blocks_even_without_open_word() -> None:
    report = mutate(
        VALID_REPORT,
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |",
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Not resolved — deferred to follow-up |",
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_open_wording_outside_review_verdict_table_does_not_block() -> None:
    report = VALID_REPORT + (
        "\n## Autonomous Decisions\n\n"
        "| # | Decision Point | Options Considered | Chose | Rationale |\n"
        "|---|----------------|--------------------|-------|-----------|\n"
        "| 1 | Important | Option A vs Option B | Option A | Left the API design open for a future iteration |\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert "BR.open_blocking_finding" not in _rules(verdict)


def test_unsupported_schema_version_fails() -> None:
    report = mutate(VALID_REPORT, "| **Schema Version** | 2 |", "| **Schema Version** | 99 |")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.schema_version" in _rules(verdict)


def test_unfilled_overall_placeholder_fails() -> None:
    report = mutate(
        VALID_REPORT,
        "### Overall: ✅ COMPLETE",
        "### Overall: {✅ COMPLETE / 🔄 IN PROGRESS / ❌ BLOCKED}",
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.tasks_incomplete" in _rules(verdict)


def test_verb_prefixed_hedge_still_blocks() -> None:
    for hedge in ("fixed? no", "Fixed - actually not", "resolved (draft, pending review)"):
        report = mutate(
            VALID_REPORT,
            "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |",
            f"| 1 | Important | Missing docstring | src/sample/parser.py:10 | {hedge} |",
        )
        verdict = _lint(report)
        assert verdict.level == Level.FAIL, hedge
        assert "BR.open_blocking_finding" in _rules(verdict), hedge


def test_demoted_review_verdict_heading_fails_closed() -> None:
    report = mutate(VALID_REPORT, "## Review Verdict", "### Review Verdict")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    section_findings = [f for f in verdict.findings if f.rule == "L2.required_section"]
    assert any(f.field == "review_verdict" for f in section_findings)
