"""Tests for BuildReportContract, run through `engine.lint`.

One test per documented BR.* rule family (PASS + FAIL, plus a legacy fork),
built on a single module-level VALID_REPORT fixture — a minimal but fully
conformant schema-v2 build report — mutated per test via the `mutate` helper
so each test's intent (what changed, what should break) stays legible.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


# --- TDD policy (BR.tdd_required_by_risk / BR.tdd_exception_invalid) --------
#
# Opt-in via the constructor's `risk_tdd_policy`/`tdd_exception_categories`
# params (both None by default, exercised above by every `_contract()`-built
# test). This block arms both with the real WORKFLOW_CONTRACTS.yaml
# `tdd_policy` shape and covers the risk-vs-TDD-mode matrix plus exception
# token validation.

RISK_TDD_POLICY = {
    "low": "recommended",
    "medium": "required_for_logic",
    "high": "required",
    "critical": "required",
}
TDD_EXCEPTION_CATEGORIES = ["non_executable_documentation", "declarative_configuration"]


def _contract_with_tdd_policy(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
        risk_tdd_policy=RISK_TDD_POLICY,
        tdd_exception_categories=TDD_EXCEPTION_CATEGORIES,
    )


def _lint_with_tdd_policy(report: str, legacy_level: Level = Level.WARN) -> Verdict:
    return lint(report, _contract_with_tdd_policy(legacy_level))


def _report_with_risk_and_tdd_mode(risk_level: str, tdd_mode: str) -> str:
    """VALID_REPORT with its `TDD Mode` value set to `tdd_mode` and a new
    `Risk Level` metadata row inserted right after it — VALID_REPORT has no
    Risk Level row of its own, so every case here mutates it in."""
    return mutate(
        VALID_REPORT,
        "| **TDD Mode** | off |\n",
        f"| **TDD Mode** | {tdd_mode} |\n| **Risk Level** | {risk_level} |\n",
    )


def test_tdd_required_by_risk_high_off_fails() -> None:
    report = _report_with_risk_and_tdd_mode("high", "off")
    verdict = _lint_with_tdd_policy(report)
    assert verdict.level == Level.FAIL
    assert "BR.tdd_required_by_risk" in _rules(verdict)


def test_tdd_required_by_risk_critical_with_parenthetical_fails() -> None:
    """Risk Level token extraction: only the first whitespace-delimited
    token is read, so an echoed parenthetical still resolves to 'critical'."""
    report = _report_with_risk_and_tdd_mode("critical (echo from DEFINE)", "off")
    verdict = _lint_with_tdd_policy(report)
    assert verdict.level == Level.FAIL
    assert "BR.tdd_required_by_risk" in _rules(verdict)


def test_tdd_required_by_risk_medium_off_warns() -> None:
    report = _report_with_risk_and_tdd_mode("medium", "off")
    verdict = _lint_with_tdd_policy(report)
    assert verdict.level == Level.WARN
    findings = [f for f in verdict.findings if f.rule == "BR.tdd_required_by_risk"]
    assert len(findings) == 1
    assert findings[0].level == Level.WARN


def test_tdd_required_by_risk_low_off_silent() -> None:
    report = _report_with_risk_and_tdd_mode("low", "off")
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_required_by_risk" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_tdd_required_by_risk_missing_risk_level_row_is_silent_adoption_path() -> None:
    verdict = _lint_with_tdd_policy(VALID_REPORT)
    assert "BR.tdd_required_by_risk" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_tdd_required_by_risk_high_with_required_mode_and_evidence_is_silent() -> None:
    report = _report_with_risk_and_tdd_mode("high", "required")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | RED | GREEN |\n"
        "|------|-----|-------|\n"
        "| Implement parser | test_parser_rejects_bad_input fails | "
        "test_parser_rejects_bad_input passes |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_required_by_risk" not in _rules(verdict)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_tdd_required_by_risk_unknown_token_is_silent() -> None:
    report = _report_with_risk_and_tdd_mode("banana", "off")
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_required_by_risk" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_tdd_exception_invalid_fails_for_unsanctioned_token() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | opt-in |")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | RED | GREEN |\n"
        "|------|-----|-------|\n"
        "| Implement parser | n/a — exception: vibes; verified by: x | n/a |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "BR.tdd_exception_invalid"]
    assert len(findings) == 1
    assert "vibes" in findings[0].message


def test_tdd_exception_invalid_passes_for_sanctioned_token() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | opt-in |")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | RED | GREEN |\n"
        "|------|-----|-------|\n"
        "| Implement parser | n/a — exception: non_executable_documentation; verified by: x | "
        "n/a |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_exception_invalid" not in _rules(verdict)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_tdd_policy_disarmed_when_constructor_params_are_none() -> None:
    report = _report_with_risk_and_tdd_mode("high", "off")
    verdict = _lint(report)  # plain _contract(): risk_tdd_policy/tdd_exception_categories None
    assert "BR.tdd_required_by_risk" not in _rules(verdict)
    assert "BR.tdd_exception_invalid" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_incidental_exception_text_in_red_excerpt_does_not_fire() -> None:
    report = _report_with_risk_and_tdd_mode("high", "required")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |\n"
        "|------|-----------|-------------------------------|-----------|--------|\n"
        '| parse config | tests/test_cfg.py | ValueError("exception: bad_config_format encountered") | 3 passed | - |\n'
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_exception_invalid" not in _rules(verdict)


def test_sanctioned_exception_grammar_still_fires_on_unknown_category() -> None:
    report = _report_with_risk_and_tdd_mode("high", "required")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |\n"
        "|------|-----------|-------------------------------|-----------|--------|\n"
        "| docs task | n/a — exception: vibes; verified by: nothing | - | - | - |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_exception_invalid" in _rules(verdict)


def test_risk_level_empty_value_is_silent() -> None:
    verdict = _lint_with_tdd_policy(_report_with_risk_and_tdd_mode("", "off"))
    assert "BR.tdd_required_by_risk" not in _rules(verdict)


def test_risk_level_capitalized_token_still_fails() -> None:
    verdict = _lint_with_tdd_policy(_report_with_risk_and_tdd_mode("High", "off"))
    assert verdict.level == Level.FAIL
    assert "BR.tdd_required_by_risk" in _rules(verdict)


def test_risk_level_template_placeholder_is_silent() -> None:
    verdict = _lint_with_tdd_policy(
        _report_with_risk_and_tdd_mode("n/a (legacy DEFINE)", "off")
    )
    assert "BR.tdd_required_by_risk" not in _rules(verdict)


def test_risk_level_trailing_whitespace_still_warns() -> None:
    verdict = _lint_with_tdd_policy(_report_with_risk_and_tdd_mode("medium   ", "off"))
    rules = _rules(verdict)
    assert "BR.tdd_required_by_risk" in rules
    assert verdict.level == Level.WARN


def test_define_literal_exception_wording_without_na_prefix_fails() -> None:
    report = _report_with_risk_and_tdd_mode("high", "required")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |\n"
        "|------|-----------|-------------------------------|-----------|--------|\n"
        "| docs | exception: vibes — trust me | - | - | - |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_exception_invalid" in _rules(verdict)


def test_define_literal_exception_wording_known_category_is_clean() -> None:
    report = _report_with_risk_and_tdd_mode("high", "required")
    report += (
        "\n## TDD Evidence\n\n"
        "| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |\n"
        "|------|-----------|-------------------------------|-----------|--------|\n"
        "| docs | exception: non_executable_documentation — markdownlint docs/ | - | - | - |\n"
    )
    verdict = _lint_with_tdd_policy(report)
    assert "BR.tdd_exception_invalid" not in _rules(verdict)


# --- Task review (BR.task_review_missing / BR.task_review_dirty) -----------
#
# Opt-in via the constructor's `task_review_verdicts` param (None by default,
# exercised above by every plain `_contract()`-built test). This block arms
# it — alone, deliberately not combined with `risk_tdd_policy`/
# `tdd_exception_categories` — with the real WORKFLOW_CONTRACTS.yaml
# `task_review.verdicts` vocabulary, covering the risk-vs-missing-review
# matrix (`BR.task_review_missing`) plus the dirty/invalid-token check
# (`BR.task_review_dirty`), which fires at any risk level independent of the
# missing rule's severity gate.

TASK_REVIEW_VERDICTS = ["clean", "clean-with-minors", "dirty", "skipped-by-policy"]


def _contract_with_task_review(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
        task_review_verdicts=TASK_REVIEW_VERDICTS,
    )


def _lint_with_task_review(report: str, legacy_level: Level = Level.WARN) -> Verdict:
    return lint(report, _contract_with_task_review(legacy_level))


def _report_with_task_ids(report: str, task_id_1: str, task_id_2: str) -> str:
    """VALID_REPORT's Task Execution table has no dedicated Task ID column
    (unlike BUILD_REPORT_TEMPLATE.md's `# | Task ID | Task | Agent | ...`) —
    the parser reads whatever sits in cells[1] (here, the Task description)
    as the task id. Replace both rows' cells[1] with real-looking ids so
    each task-review test's intent stays legible."""
    report = mutate(
        report,
        "| 1 | Implement parser | python-pro | ✅ |",
        f"| 1 | {task_id_1} | python-pro | ✅ |",
    )
    return mutate(
        report,
        "| 2 | Write tests | test-generator | ✅ |",
        f"| 2 | {task_id_2} | test-generator | ✅ |",
    )


def _report_with_risk_level(report: str, risk_level: str) -> str:
    """VALID_REPORT with a `Risk Level` metadata row inserted after `TDD
    Mode` — TDD Mode itself stays `off` and `_contract_with_task_review`
    never passes `risk_tdd_policy`, so `BR.tdd_required_by_risk` stays
    disarmed and findings stay isolated to the task-review rules."""
    return mutate(
        report,
        "| **TDD Mode** | off |\n",
        f"| **TDD Mode** | off |\n| **Risk Level** | {risk_level} |\n",
    )


def _task_reviews_section(rows: list[tuple[str, str]]) -> str:
    """Render a minimal `## Task Reviews` section: only cells[1] (Task ID)
    and cells[4] (Verdict) are read by the parser, but all 5 columns are
    populated to mirror BUILD_REPORT_TEMPLATE.md's shape."""
    lines = [
        "\n## Task Reviews\n",
        "| # | Task ID | Risk | Reviewer | Verdict |",
        "|---|---------|------|----------|---------|",
    ]
    lines.extend(
        f"| {i} | {task_id} | high | @reviewer | {verdict} |"
        for i, (task_id, verdict) in enumerate(rows, start=1)
    )
    return "\n".join(lines) + "\n"


def test_task_review_missing_high_risk_two_tasks_no_reviews_fails() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "high")
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "BR.task_review_missing"]
    assert len(findings) == 2


def test_task_review_all_tasks_reviewed_high_risk_passes() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "high")
    report += _task_reviews_section([("TASK-001", "clean"), ("TASK-002", "clean-with-minors")])
    verdict = _lint_with_task_review(report)
    assert "BR.task_review_missing" not in _rules(verdict)
    assert "BR.task_review_dirty" not in _rules(verdict)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_task_review_one_task_unreviewed_names_that_task() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "high")
    report += _task_reviews_section([("TASK-001", "clean")])
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "BR.task_review_missing"]
    assert len(findings) == 1
    assert "TASK-002" in findings[0].message
    assert "TASK-001" not in findings[0].message


def test_task_review_missing_medium_risk_warns_not_fails() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "medium")
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.WARN
    findings = [f for f in verdict.findings if f.rule == "BR.task_review_missing"]
    assert len(findings) == 2
    assert all(f.level == Level.WARN for f in findings)


def test_task_review_missing_low_risk_silent() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "low")
    verdict = _lint_with_task_review(report)
    assert "BR.task_review_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_task_review_missing_no_risk_level_row_silent() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    verdict = _lint_with_task_review(report)  # VALID_REPORT has no Risk Level row
    assert "BR.task_review_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_task_review_dirty_verdict_fails_independent_of_risk() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    # No Risk Level row at all: BR.task_review_missing stays silent (no risk
    # token), but BR.task_review_dirty is not gated on risk at all.
    report += _task_reviews_section([("TASK-001", "dirty"), ("TASK-002", "clean")])
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "BR.task_review_dirty"]
    assert len(findings) == 1
    assert "TASK-001" in findings[0].message
    assert "BR.task_review_missing" not in _rules(verdict)


def test_task_review_invalid_verdict_token_fails() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report += _task_reviews_section([("TASK-001", "sketchy"), ("TASK-002", "clean")])
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "BR.task_review_dirty"]
    assert len(findings) == 1
    assert findings[0].found == "sketchy"


def test_task_review_skipped_by_policy_is_valid() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "high")
    report += _task_reviews_section([("TASK-001", "skipped-by-policy"), ("TASK-002", "clean")])
    verdict = _lint_with_task_review(report)
    assert "BR.task_review_dirty" not in _rules(verdict)
    assert "BR.task_review_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_task_review_v1_report_with_dash_task_ids_has_no_missing_findings() -> None:
    report = _report_with_task_ids(VALID_REPORT, "-", "-")
    report = _report_with_risk_level(report, "high")
    verdict = _lint_with_task_review(report)
    assert "BR.task_review_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_task_review_disarmed_when_constructor_param_is_none() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-001", "TASK-002")
    report = _report_with_risk_level(report, "high")
    verdict = _lint(report)  # plain _contract(): task_review_verdicts is None
    assert "BR.task_review_missing" not in _rules(verdict)
    assert "BR.task_review_dirty" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_decoy_task_reviews_heading_does_not_shadow_real_section() -> None:
    report = _report_with_risk_level(_report_with_task_ids(VALID_REPORT, "TASK-A-001", "TASK-B-001"), "high")
    decoy = (
        "\n## Task Reviews Notes\n\n"
        "Prose mentioning a dirty verdict that must not count.\n"
        "| 1 | FAKE-999 | high | @nobody | dirty | 0 / 0 | 0/1 |\n"
    )
    real = _task_reviews_section([("TASK-A-001", "clean"), ("TASK-B-001", "clean")])
    verdict = _lint_with_task_review(report + decoy + real)
    rules = _rules(verdict)
    assert "BR.task_review_missing" not in rules
    assert "BR.task_review_dirty" not in rules


def test_clean_decoy_cannot_mask_a_dirty_real_section() -> None:
    report = _report_with_risk_level(_report_with_task_ids(VALID_REPORT, "TASK-A-001", "TASK-B-001"), "high")
    decoy = (
        "\n## Task Reviews Draft\n\n"
        "| 1 | TASK-A-001 | high | @x | clean | 0 / 0 | 0/1 |\n"
        "| 2 | TASK-B-001 | high | @x | clean | 0 / 0 | 0/1 |\n"
    )
    real = _task_reviews_section([("TASK-A-001", "clean"), ("TASK-B-001", "dirty")])
    verdict = _lint_with_task_review(report + decoy + real)
    assert "BR.task_review_dirty" in _rules(verdict)


def test_placeholder_review_row_is_skipped_not_invalid() -> None:
    report = _report_with_risk_level(_report_with_task_ids(VALID_REPORT, "TASK-A-001", "TASK-B-001"), "low")
    placeholder = (
        "\n## Task Reviews\n\n"
        "| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |\n"
        "|---|---------|------|----------|---------|----------------------|------------|\n"
        "| 1 | {TASK-AREA-001} | {low/medium/high/critical} | {@reviewer / (self)} | {clean / clean-with-minors / dirty / skipped-by-policy} | {0 / 1} | {0-1}/1 |\n"
    )
    verdict = _lint_with_task_review(report + placeholder)
    assert "BR.task_review_dirty" not in _rules(verdict)


# --- Traceability matrix coverage (BR.must_uncovered / BR.matrix_missing) --
#
# Opt-in via the constructor's `matrix_must_coverage` param (`False` by
# default, exercised above by every plain `_contract()`-built test). This
# block arms it alone — deliberately not combined with `risk_tdd_policy`/
# `task_review_verdicts` — covering `BR.must_uncovered` (MUST rows of a
# filled `## Traceability Matrix` needing a filled Tests cell and a passing
# Result, unless Tests records the sanctioned `exception:` grammar) and
# `BR.matrix_missing` (a wholly absent matrix WARNing only at high/critical
# Risk Level).


def _contract_with_matrix(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
        matrix_must_coverage=True,
    )


def _lint_with_matrix(report: str, legacy_level: Level = Level.WARN) -> Verdict:
    return lint(report, _contract_with_matrix(legacy_level))


def _filled_matrix_section(rows: list[tuple[str, str, str, str]]) -> str:
    """Render a filled `## Traceability Matrix` section: build-side 8-cell
    rows `| # | REQ | Priority | Tasks | Tests | Verification Type | Result |
    Review |` — only cells 1/2/4/6 (REQ/Priority/Tests/Result) are read by
    the parser; Tasks (3) and Verification Type (5) are filled with
    placeholders to mirror the template shape. `rows` is
    `(req, priority, tests, result)`."""
    lines = [
        "\n## Traceability Matrix\n",
        "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |",
        "|---|-----|----------|-------|-------|-------------------|--------|--------|",
    ]
    lines.extend(
        f"| {i} | {req} | {priority} | TASK-A | {tests} | unit | {result} | clean |"
        for i, (req, priority, tests, result) in enumerate(rows, start=1)
    )
    return "\n".join(lines) + "\n"


def test_must_row_with_tests_and_pass_result_has_no_finding() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "MUST", "tests/test_parser.py", "Pass")]
    )
    verdict = _lint_with_matrix(report)
    assert "BR.must_uncovered" not in _rules(verdict)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_must_row_with_dash_tests_fails_must_uncovered() -> None:
    report = VALID_REPORT + _filled_matrix_section([("REQ-1", "MUST", "-", "Pass")])
    verdict = _lint_with_matrix(report)
    assert verdict.level == Level.FAIL
    assert "BR.must_uncovered" in _rules(verdict)


def test_must_row_with_fail_result_fails_must_uncovered() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "MUST", "tests/test_parser.py", "Fail")]
    )
    verdict = _lint_with_matrix(report)
    assert verdict.level == Level.FAIL
    assert "BR.must_uncovered" in _rules(verdict)


def test_must_row_with_exception_grammar_is_exempt() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "MUST", "exception: contractual — cite", "Fail")]
    )
    verdict = _lint_with_matrix(report)
    assert "BR.must_uncovered" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_should_row_with_empty_tests_has_no_finding() -> None:
    report = VALID_REPORT + _filled_matrix_section([("REQ-2", "SHOULD", "", "Fail")])
    verdict = _lint_with_matrix(report)
    assert "BR.must_uncovered" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_matrix_missing_warns_high_risk_silent_otherwise() -> None:
    high_no_matrix = _report_with_risk_level(VALID_REPORT, "high")
    verdict = _lint_with_matrix(high_no_matrix)
    assert verdict.level == Level.WARN
    assert "BR.matrix_missing" in _rules(verdict)

    medium_no_matrix = _report_with_risk_level(VALID_REPORT, "medium")
    verdict = _lint_with_matrix(medium_no_matrix)
    assert "BR.matrix_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS

    high_with_matrix = _report_with_risk_level(VALID_REPORT, "high") + _filled_matrix_section(
        [("REQ-1", "MUST", "tests/test_parser.py", "Pass")]
    )
    verdict = _lint_with_matrix(high_with_matrix)
    assert "BR.matrix_missing" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_unfilled_placeholder_must_row_fails_coverage() -> None:
    report = _report_with_risk_level(
        _report_with_task_ids(VALID_REPORT, "TASK-A-001", "TASK-B-001"), "high"
    )
    report += (
        "\n## Traceability Matrix\n\n"
        "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |\n"
        "|---|-----|----------|-------|-------|-------------------|--------|--------|\n"
        "| 1 | REQ-001 | MUST | TASK-A-001 | {tests} | {type} | {Pass / Fail} | {clean} |\n"
    )
    verdict = lint(report, _contract_with_matrix())
    assert "BR.must_uncovered" in [f.rule for f in verdict.findings]


def test_decoy_matrix_heading_does_not_mask_missing_matrix() -> None:
    report = _report_with_risk_level(
        _report_with_task_ids(VALID_REPORT, "TASK-A-001", "TASK-B-001"), "high"
    )
    report += "\n## Traceability Matrix Notes\n\nProse only.\n"
    verdict = lint(report, _contract_with_matrix())
    assert "BR.matrix_missing" in [f.rule for f in verdict.findings]


# --- MD.table_malformed / MD.table_malformed (fail-closed) ----
# Codex review findings 2–3: truncated or placeholder-bearing rows were
# silently dropped, letting a MUST row or a dirty verdict hide by truncation.


def _raw_matrix_section(raw_rows: list[str]) -> str:
    lines = [
        "\n## Traceability Matrix\n",
        "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |",
        "|---|-----|----------|-------|-------|-------------------|--------|--------|",
    ]
    lines.extend(raw_rows)
    return "\n".join(lines) + "\n"


def test_truncated_must_matrix_row_fails_malformed() -> None:
    report = VALID_REPORT + _raw_matrix_section(["| 1 | REQ-1 | MUST | TASK-A |"])
    verdict = _lint_with_matrix(report)
    assert verdict.level == Level.FAIL
    assert "MD.table_malformed" in _rules(verdict)


@pytest.mark.parametrize("cells", list(range(2, 8)))
def test_matrix_row_every_short_cardinality_fails(cells: int) -> None:
    row = "| 1 | " + " | ".join(["x"] * (cells - 1)) + " |"
    report = VALID_REPORT + _raw_matrix_section([row])
    verdict = _lint_with_matrix(report)
    assert "MD.table_malformed" in _rules(verdict)
    assert verdict.level == Level.FAIL


def test_placeholder_req_matrix_row_fails_malformed() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("{REQ id}", "MUST", "tests/test_x.py", "Pass")]
    )
    verdict = _lint_with_matrix(report)
    assert "MD.table_malformed" in _rules(verdict)


def test_placeholder_priority_matrix_row_fails_malformed() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "{MUST/SHOULD}", "tests/test_x.py", "Pass")]
    )
    verdict = _lint_with_matrix(report)
    assert "MD.table_malformed" in _rules(verdict)


def test_malformed_row_is_reported_AND_still_seen_by_coverage() -> None:
    """PR B's invariant in action: the truncated MUST row is no longer dropped,
    so it is reported as malformed AND counted as uncovered. Under PR A it
    vanished from coverage entirely — reporting both is strictly more
    informative and strictly more fail-closed."""
    report = VALID_REPORT + _raw_matrix_section(
        [
            "| 1 | REQ-1 | MUST | TASK-A | tests/test_x.py | unit | Pass | clean |",
            "| 2 | REQ-2 | MUST | TASK-B |",
        ]
    )
    rules = _rules(_lint_with_matrix(report))
    assert rules.count("MD.table_malformed") == 1
    assert "BR.must_uncovered" in rules


def test_intact_matrix_rows_produce_no_malformed_finding() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "MUST", "tests/test_x.py", "Pass")]
    )
    assert "MD.table_malformed" not in _rules(_lint_with_matrix(report))


def test_short_review_row_hiding_dirty_fails_malformed_at_low_risk() -> None:
    # Codex finding 3: at low risk the missing-rule is silent by policy and a
    # 4-cell row never reached task_review_rows — a dirty verdict could hide.
    report = _report_with_risk_level(
        _report_with_task_ids(VALID_REPORT, "TASK-1", "TASK-2"), "low"
    )
    report += (
        "\n## Task Reviews\n\n"
        "| # | Task ID | Risk | Reviewer | Verdict |\n"
        "|---|---------|------|----------|---------|\n"
        "| 1 | TASK-1 | low | dirty |\n"
    )
    verdict = _lint_with_task_review(report)
    assert verdict.level == Level.FAIL
    assert "MD.table_malformed" in _rules(verdict)


def test_placeholder_verdict_review_row_fails_malformed() -> None:
    report = _report_with_risk_level(
        _report_with_task_ids(VALID_REPORT, "TASK-1", "TASK-2"), "low"
    )
    report += _task_reviews_section([("TASK-1", "{verdict}")])
    verdict = _lint_with_task_review(report)
    assert "MD.table_malformed" in _rules(verdict)
    assert verdict.level == Level.FAIL


def test_intact_review_rows_produce_no_malformed_finding() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-1", "TASK-2")
    report += _task_reviews_section([("TASK-1", "clean"), ("TASK-2", "clean")])
    assert "MD.table_malformed" not in _rules(_lint_with_task_review(report))


# --- exact section addressing + MD.duplicate_contract_section -----------------
# Remediation spec §6 (PR A): a heading whose slug merely STARTS WITH a
# contract section's slug could redefine the scanned scope, hiding open
# blocking findings (§3.1 repro produced PASS). Addressing is now exact, all
# matches are scanned as a union, and duplicates are a FAIL.

_OPEN_CRITICAL_ROW = (
    "| 2 | Critical | data loss on migrate | src/migrate.py | OPEN |"
)
_OPEN_IMPORTANT_ROW = (
    "| 2 | Important | unbounded retry | src/retry.py | pending |"
)


def _with_review_row(report: str, row: str) -> str:
    """Append a findings row to the real `## Review Verdict` section."""
    return mutate(
        report,
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |",
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |\n" + row,
    )


def _decoy_before(report: str, heading: str = "## Review Verdict Notes") -> str:
    return mutate(report, "## Review Verdict\n", f"{heading}\n\nSide notes, no findings.\n\n## Review Verdict\n")


def test_spec_3_1_repro_decoy_before_real_section_now_fails() -> None:
    """The exact reproduction from remediation spec §3.1: a
    `## Review Verdict Notes` decoy ahead of the real section, which carries
    an OPEN Critical finding. This produced PASS before PR A."""
    report = _decoy_before(_with_review_row(VALID_REPORT, _OPEN_CRITICAL_ROW))
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_decoy_after_real_section_leaves_scope_intact() -> None:
    report = _with_review_row(VALID_REPORT, _OPEN_IMPORTANT_ROW)
    report += "\n## Review Verdict Notes\n\nTrailing commentary.\n"
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_decoy_heading_is_inert_as_a_section_address() -> None:
    # A decoy is not the section: its non-findings content contributes nothing,
    # and it raises no duplicate (its slug is not a contract section).
    report = VALID_REPORT + (
        "\n## Review Verdict Notes\n\n"
        "| # | Note | Author |\n|---|------|--------|\n"
        "| 1 | Critical thinking was applied | @me |\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_a_findings_table_anywhere_still_blocks() -> None:
    # Safety net: the findings table is identified by its own header
    # (Severity + Resolution), so an unresolved blocking row is caught wherever
    # it sits — parking it under a decoy heading is not a hiding place.
    report = VALID_REPORT + (
        "\n## Review Verdict Notes\n\n"
        "| # | Severity | Description | Location | Resolution |\n"
        "|---|----------|-------------|----------|------------|\n"
        + _OPEN_CRITICAL_ROW
        + "\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_duplicate_review_verdict_section_fails() -> None:
    report = mutate(VALID_REPORT, "## Review Verdict\n", "## Review Verdict\n\nFirst copy.\n\n## Review Verdict\n")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    findings = [f for f in verdict.findings if f.rule == "MD.duplicate_contract_section"]
    assert len(findings) == 1
    assert "Review Verdict" in (findings[0].field or "")


def test_duplicate_section_message_names_the_heading_lines() -> None:
    report = mutate(VALID_REPORT, "## Review Verdict\n", "## Review Verdict\n\nFirst copy.\n\n## Review Verdict\n")
    finding = next(f for f in _lint(report).findings if f.rule == "MD.duplicate_contract_section")
    # Two 1-indexed heading line numbers, in document order.
    assert finding.found is not None
    numbers = [int(tok) for tok in finding.found.replace(",", " ").split() if tok.isdigit()]
    assert len(numbers) == 2 and numbers[0] < numbers[1]


def test_union_scan_reads_blocking_rows_from_the_second_copy() -> None:
    """Fail-closed: a duplicated section is never a hiding place — an open
    blocking row in ANY copy blocks, alongside the duplicate finding."""
    second_copy = (
        "## Review Verdict\n\n"
        "| # | Severity | Description | Location | Resolution |\n"
        "|---|----------|-------------|----------|------------|\n"
        + _OPEN_CRITICAL_ROW
        + "\n\n"
    )
    report = mutate(VALID_REPORT, "## Acceptance Test Verification\n", second_copy + "## Acceptance Test Verification\n")
    rules = _rules(_lint(report))
    assert "MD.duplicate_contract_section" in rules
    assert "BR.open_blocking_finding" in rules


def test_duplicate_task_execution_section_fails() -> None:
    report = mutate(
        VALID_REPORT,
        "## Files Created\n",
        "## Task Execution with Agent Attribution\n\n| # | Task | Agent | Status |\n|---|------|-------|--------|\n| 1 | dup | x | ✅ |\n\n## Files Created\n",
    )
    assert "MD.duplicate_contract_section" in _rules(_lint(report))


def test_duplicate_section_fails_even_when_its_family_is_disarmed() -> None:
    # `## Task Reviews` rules are opt-in, but a duplicated contract section is
    # a structural defect regardless of arming (always-on rule).
    dup = "## Task Reviews\n\n| # | Task ID | Risk | Reviewer | Verdict |\n|---|---------|------|----------|---------|\n| 1 | TASK-1 | low | @r | clean |\n\n"
    report = VALID_REPORT + "\n" + dup + dup
    assert "MD.duplicate_contract_section" in _rules(_lint(report))


def test_demoted_review_verdict_heading_is_a_missing_required_section() -> None:
    report = mutate(VALID_REPORT, "## Review Verdict\n", "### Review Verdict\n")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "L2.required_section" in _rules(verdict)


def test_open_critical_in_the_real_section_fails() -> None:
    verdict = _lint(_with_review_row(VALID_REPORT, _OPEN_CRITICAL_ROW))
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_open_important_in_the_real_section_fails() -> None:
    verdict = _lint(_with_review_row(VALID_REPORT, _OPEN_IMPORTANT_ROW))
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_resolution_fixed_in_sha_is_not_blocking() -> None:
    row = "| 2 | Critical | race condition | src/x.py | fixed in 9f2a1c0 |"
    verdict = _lint(_with_review_row(VALID_REPORT, row))
    assert "BR.open_blocking_finding" not in _rules(verdict)


@pytest.mark.parametrize(
    "resolution",
    ["fixed? no", "Fixed - actually not", "Not resolved", "will fix in a follow-up", ""],
)
def test_look_alike_resolutions_still_block(resolution: str) -> None:
    row = f"| 2 | Critical | race condition | src/x.py | {resolution} |"
    assert "BR.open_blocking_finding" in _rules(_lint(_with_review_row(VALID_REPORT, row)))


def test_bare_tdd_evidence_heading_addresses_the_section() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | required |")
    report += (
        "\n## TDD Evidence\n\n"
        "| # | Task | RED | GREEN |\n|---|------|-----|-------|\n"
        "| 1 | parser | failing test | passing test |\n"
    )
    assert "BR.tdd_evidence_missing" not in _rules(_lint(report))


def test_full_template_tdd_evidence_heading_addresses_the_section() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | required |")
    report += (
        "\n## TDD Evidence (required when TDD Mode != off)\n\n"
        "| # | Task | RED | GREEN |\n|---|------|-----|-------|\n"
        "| 1 | parser | failing test | passing test |\n"
    )
    assert "BR.tdd_evidence_missing" not in _rules(_lint(report))


def test_tdd_evidence_notes_decoy_is_not_the_section() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | required |")
    report += (
        "\n## TDD Evidence Notes\n\n"
        "| # | Task | RED | GREEN |\n|---|------|-----|-------|\n"
        "| 1 | parser | failing test | passing test |\n"
    )
    assert "BR.tdd_evidence_missing" in _rules(_lint(report))



def _real_build_contract() -> BuildReportContract:
    """The contract the repo actually ships, assembled from the canonical
    WORKFLOW_CONTRACTS.yaml — so the dogfood below exercises the real arming
    (metrics, traceability, task_review, tdd_policy), not a synthetic subset."""
    from spec_linter import cli

    contracts_file = Path(__file__).resolve().parents[3] / (
        ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
    )
    data = cli._load_contracts_data(contracts_file)
    return cli._build_report_contract(data, contracts_file, "warn")


# --- archived-corpus dogfood (spec §6.7 last bullet) --------------------------
# Exact addressing must not invalidate a single archived report: every one of
# them is template-conform, so the migration is provably non-breaking.

_ARCHIVE = Path(__file__).resolve().parents[3] / ".claude/sdd/archive"

_ADDRESSING_RULES = {"MD.duplicate_contract_section", "L2.required_section"}


def _archived_reports() -> list[Path]:
    return sorted(_ARCHIVE.glob("*/BUILD_REPORT_*.md"))


@pytest.mark.skipif(not _ARCHIVE.is_dir(), reason="archive corpus not present")
def test_archive_corpus_is_not_empty() -> None:
    # Guards the two tests below from silently passing on an empty glob.
    assert len(_archived_reports()) >= 10


@pytest.mark.skipif(not _ARCHIVE.is_dir(), reason="archive corpus not present")
def test_no_archived_report_gains_an_addressing_finding() -> None:
    contract = _real_build_contract()
    offenders: dict[str, list[str]] = {}
    for report in _archived_reports():
        rules = {f.rule for f in lint(report.read_text(), contract).findings}
        hit = sorted(rules & _ADDRESSING_RULES)
        if hit:
            offenders[report.parent.name] = hit
    assert offenders == {}


@pytest.mark.skipif(not _ARCHIVE.is_dir(), reason="archive corpus not present")
def test_no_archived_report_fails_under_exact_addressing() -> None:
    contract = _real_build_contract()
    failures = {
        report.parent.name: sorted(
            f.rule for f in lint(report.read_text(), contract).findings if f.level == Level.FAIL
        )
        for report in _archived_reports()
    }
    assert {name: rules for name, rules in failures.items() if rules} == {}


def test_stray_h1_cannot_shrink_the_review_verdict_scope() -> None:
    """Fix-round regression: a same-or-higher-level boundary let `# stray`
    truncate the section and hide the Critical row below it (PASS)."""
    row = _OPEN_CRITICAL_ROW
    report = mutate(
        VALID_REPORT,
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |",
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
        "\n\n# stray\n\n" + row,
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_hash_comment_in_a_quoted_snippet_cannot_shrink_the_scope() -> None:
    """Same regression without any adversarial intent: reports quote shell and
    YAML constantly, and `# TODO: ...` inside a fence is not a heading."""
    report = mutate(
        VALID_REPORT,
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |",
        "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
        "\n\n```bash\n# TODO: unsafe eval left in prod\n```\n\n" + _OPEN_CRITICAL_ROW,
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_duplicated_tdd_evidence_rows_are_counted_per_section() -> None:
    report = mutate(VALID_REPORT, "| **TDD Mode** | off |", "| **TDD Mode** | required |")
    one = (
        "\n## TDD Evidence\n\n| # | Task | RED | GREEN |\n|---|------|-----|-------|\n"
        "| 1 | parser | failing | passing |\n"
    )
    parsed = _contract().parse(report + one + one)
    assert parsed.tdd_evidence_rows == 2  # not 3 (union minus a single header)


# --- boundary-vocabulary regressions (round-2 structural fix) -----------------


def _review_section_with(middle: str) -> str:
    resolved = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
    return mutate(
        VALID_REPORT, resolved, f"{resolved}\n\n{middle}\n\n{_OPEN_CRITICAL_ROW}"
    )


@pytest.mark.parametrize(
    "middle",
    [
        "## Notes",
        "## Review Verdict Notes",
        "# stray",
        "<!--\n## superseded\n-->",
        "<!-- ## Task Reviews -->",
        "```bash\n# TODO: unsafe eval left in prod\n```",
        "````\n```\n## old draft\n```\n````",
        "    # indented code comment",
        "~~~text\n## Task Execution with Agent Attribution\n~~~",
        # Recognised boundary headings that ARE legitimate elsewhere: moving or
        # duplicating one inside the section truncates the scope, so the
        # table-anchored safety net has to catch the row regardless.
        "## Files Created\n\n- src/x.py",
        "## Verification Results\n\n- `pytest` - ok",
        # Severing the row from its table header with intervening content: a
        # fragment inherits the nearest preceding header, so it stays a finding.
        "- a bullet\n- another bullet",
        "some interleaved prose",
        "## Verification Results\n\n- `pytest` - ok",
    ],
)
def test_nothing_can_hide_an_open_critical_from_the_review_scan(middle: str) -> None:
    verdict = _lint(_review_section_with(middle))
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


def test_clean_report_stays_pass_under_the_boundary_vocabulary() -> None:
    # The conservative boundary must not manufacture findings on a good report.
    verdict = _lint(VALID_REPORT)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_boundary_vocabulary_covers_every_template_section() -> None:
    """Self-maintaining guard: if BUILD_REPORT_TEMPLATE.md grows a section and
    it is not added to _BOUNDARY_SLUGS, the preceding section would silently
    swallow it — this test fails first."""
    import re as _re

    from spec_linter.contracts.build_report import _BOUNDARY_SLUGS
    from spec_linter.sections import slug as _slug

    template = (
        Path(__file__).resolve().parents[3] / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
    ).read_text()
    template_slugs = {
        _slug(m.group(1)) for m in _re.finditer(r"^##\s+(.*\S)\s*$", template, _re.M)
    }
    assert template_slugs <= _BOUNDARY_SLUGS, sorted(template_slugs - _BOUNDARY_SLUGS)


def test_moved_boundary_heading_cannot_hide_a_critical() -> None:
    """The hardest variant: a recognised boundary is MOVED (not duplicated)
    into the section, so no duplicate finding fires — only the table-anchored
    safety net can catch the row."""
    resolved = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
    report = mutate(
        VALID_REPORT,
        resolved,
        f"{resolved}\n\n## Files Created\n\n- src/x.py\n\n{_OPEN_CRITICAL_ROW}",
    )
    report = mutate(
        report,
        "## Files Created\n\n- `src/sample/parser.py`\n- `tests/test_parser.py`\n\n",
        "",
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)
    assert "MD.duplicate_contract_section" not in _rules(verdict)


def test_intact_non_findings_table_never_feeds_the_safety_net() -> None:
    """Precision guard for the net: a free-text table whose header is intact is
    not a findings table, whatever its cells happen to say."""
    report = VALID_REPORT + (
        "\n## Issues Encountered\n\n"
        "| # | Issue | Resolution | Time Impact |\n"
        "|---|-------|------------|-------------|\n"
        "| 1 | Critical | still open, tracked upstream | +2h |\n"
    )
    verdict = _lint(report)
    assert "BR.open_blocking_finding" not in _rules(verdict)


def test_split_legitimate_table_is_not_read_as_findings() -> None:
    """A stray blank line halves an ordinary table; the fragment inherits its
    real (non-findings) header, so an "Important"-valued cell is not a finding.
    Without inheritance this was a false FAIL on plausible hand-edited reports."""
    report = VALID_REPORT + (
        "\n## Autonomous Decisions\n\n"
        "| # | Decision Point | Options | Chose | Rationale |\n"
        "|---|----------------|---------|-------|-----------|\n\n"
        "| 1 | Important | A vs B | A | deferred to a follow-up |\n"
    )
    verdict = _lint(report)
    assert "BR.open_blocking_finding" not in _rules(verdict)


def test_findings_table_quoted_inside_a_fence_is_illustration() -> None:
    """Row scanning shares `content_lines`, so a worked example inside a fence
    is quotation — the same opacity heading detection has."""
    report = VALID_REPORT + (
        "\n## Deviations from Design\n\nBefore the fix a finding looked like:\n\n"
        "```markdown\n"
        "| # | Severity | Description | Location | Resolution |\n"
        "|---|----------|-------------|----------|------------|\n"
        "| 1 | Critical | illustration only | x.py |  |\n"
        "```\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.PASS


@pytest.mark.parametrize(
    "severity",
    ["Critical", "CRITICAL", "Critical (F1)", "**Critical**", "critical/high", "🔴 Critical"],
)
def test_severity_decoration_cannot_hide_meaning(severity: str) -> None:
    row = f"| 2 | {severity} | SQL injection | src/q.py | OPEN |"
    assert "BR.open_blocking_finding" in _rules(_lint(_with_review_row(VALID_REPORT, row)))


@pytest.mark.parametrize("severity", ["Minor", "Info", "nit"])
def test_non_blocking_severities_still_do_not_block(severity: str) -> None:
    row = f"| 2 | {severity} | cosmetic | src/q.py | recorded |"
    assert "BR.open_blocking_finding" not in _rules(_lint(_with_review_row(VALID_REPORT, row)))


def test_headerless_table_in_a_later_section_does_not_inherit_findings_identity() -> None:
    """Round-4 review FP: inheritance reached across unrelated sections, so a
    decision log whose author omitted the header inherited "findings" from the
    Review Verdict table. Width matching scopes inheritance to genuine
    continuations (same column count), not to any later headerless table."""
    report = VALID_REPORT + (
        "\n## Autonomous Decisions\n\nDecision log (header omitted by the author):\n\n"
        "| 1 | Important | escalate per policy | deferred |\n"
    )
    verdict = _lint(report)
    assert "BR.open_blocking_finding" not in _rules(verdict)
    assert verdict.level == Level.PASS


def test_severed_continuation_of_the_findings_table_still_inherits() -> None:
    """The other side of the width check: a real continuation keeps the table's
    column count, so severing it with a boundary heading changes nothing."""
    resolved = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
    report = mutate(
        VALID_REPORT,
        resolved,
        f"{resolved}\n\n## Files Created\n\n- src/x.py\n\n{_OPEN_CRITICAL_ROW}",
    )
    assert "BR.open_blocking_finding" in _rules(_lint(report))


# --- authorized fix-round override (v3.19.0) ---------------------------------
# The budget exists to stop thrashing; exceeding it must be a HUMAN decision,
# recorded in the artifact — not a silent overrun and not a policy change.
# Mirrors the risk_profile `override: {applied, author, rationale}` precedent.

_OVERRIDE_CONFIG = {"requires": ["author", "rationale"]}


def _contract_with_override(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
        fix_rounds_override=_OVERRIDE_CONFIG,
    )


def _with_fix_rounds(value: str) -> str:
    return mutate(VALID_REPORT, "| **Fix rounds used** | 0/2 |", f"| **Fix rounds used** | {value} |")


def test_over_budget_without_override_still_fails() -> None:
    verdict = lint(_with_fix_rounds("4/2"), _contract_with_override())
    assert verdict.level == Level.FAIL
    assert "BR.fix_rounds_budget" in _rules(verdict)


def test_over_budget_with_authorized_override_warns_not_fails() -> None:
    verdict = lint(
        _with_fix_rounds("4/2 (override: author=maintainer, rationale=live Critical still open)"),
        _contract_with_override(),
    )
    assert verdict.level == Level.WARN
    findings = [f for f in verdict.findings if f.rule == "BR.fix_rounds_override"]
    assert len(findings) == 1
    assert "maintainer" in (findings[0].found or "")


def test_override_without_rationale_fails() -> None:
    verdict = lint(
        _with_fix_rounds("4/2 (override: author=maintainer, rationale=)"), _contract_with_override()
    )
    assert verdict.level == Level.FAIL


def test_override_is_opt_in_and_ignored_when_unconfigured() -> None:
    # Strict contract (no override block): the override clause buys nothing.
    verdict = _lint(_with_fix_rounds("4/2 (override: author=x, rationale=y)"))
    assert verdict.level == Level.FAIL


def test_override_does_not_excuse_a_diverging_budget() -> None:
    verdict = lint(
        _with_fix_rounds("4/9 (override: author=maintainer, rationale=whatever)"),
        _contract_with_override(),
    )
    assert verdict.level == Level.FAIL
    assert any("diverges" in f.message for f in verdict.findings)


def test_within_budget_stays_clean_under_the_override_contract() -> None:
    verdict = lint(VALID_REPORT, _contract_with_override())
    assert verdict.level == Level.PASS


# --- PR B: the five residuals PR A deferred, each named ------------------------
# Repros verbatim from docs/reviews/2026-07-30-exact-sections-residuals-for-pr-b.md.
# Each produced a full PASS on an unresolved Critical before the structural parser.

def _real_contract():
    from pathlib import Path as _P

    from spec_linter import cli

    cf = _P(__file__).resolve().parents[3] / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
    return cli._build_report_contract(cli._load_contracts_data(cf), cf, "warn")


_RESOLVED_ROW = "| 1 | Important | Missing docstring | src/sample/parser.py:10 | Fixed in abc1234 |"
_SEVER = "\n\n## Files Created\n\n- src/x.py\n\n"


def _sever(block: str, *, moved: bool = False) -> str:
    report = mutate(VALID_REPORT, _RESOLVED_ROW, _RESOLVED_ROW + block)
    if moved:
        report = mutate(
            report,
            "## Files Created\n\n- `src/sample/parser.py`\n- `tests/test_parser.py`\n\n",
            "",
        )
    return report


@pytest.mark.parametrize("moved", [False, True], ids=["duplicated", "moved"])
def test_R1_renamed_resolution_column_no_longer_hides_a_critical(moved: bool) -> None:
    block = _SEVER + (
        "| # | Severity | Description | Location | Status |\n"
        "|---|----------|-------------|----------|--------|\n"
        "| 1 | Critical | SQL injection | db.py |  |\n"
    )
    assert lint(_sever(block, moved=moved), _real_contract()).level == Level.FAIL


def test_R2_row_without_a_leading_number_no_longer_hides_a_critical() -> None:
    block = "\n| Critical | SQL injection | db.py:42 |  |"
    assert lint(_sever(block), _real_contract()).level == Level.FAIL


def test_R3_raw_html_table_is_forbidden() -> None:
    block = "\n\n<table><tr><td>Critical</td><td>SQL injection</td></tr></table>"
    verdict = lint(_sever(block), _real_contract())
    assert verdict.level == Level.FAIL
    assert "MD.html_table_forbidden" in _rules(verdict)


def test_R4_unrecognised_severity_word_blocks() -> None:
    block = "\n| 2 | Blocker | SQL injection | db.py | OPEN |"
    verdict = lint(_sever(block), _real_contract())
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


@pytest.mark.parametrize(
    "row",
    [
        "| 2 | Critical | SQL injection | db.py |  | padding |",  # wider
        "| 2 | Critical | SQL injection |",  # narrower
    ],
    ids=["padded", "narrow"],
)
def test_R5_severed_row_of_any_width_no_longer_hides_a_critical(row: str) -> None:
    assert lint(_sever(_SEVER + row, moved=True), _real_contract()).level == Level.FAIL


def test_the_clean_fixture_still_passes_under_the_real_contract() -> None:
    # The cry-wolf guard: none of the above may cost a false positive.
    verdict = lint(VALID_REPORT, _real_contract())
    assert "MD.table_malformed" not in _rules(verdict)
    assert "BR.open_blocking_finding" not in _rules(verdict)


# --- §7.6 within-artifact matrix rules ----------------------------------------


def test_duplicate_req_id_is_reported() -> None:
    report = VALID_REPORT + _filled_matrix_section(
        [("REQ-1", "MUST", "t.py", "Pass"), ("REQ-1", "MUST", "t.py", "Pass")]
    )
    assert "MD.duplicate_identifier" in _rules(_lint_with_matrix(report))


def test_matrix_present_but_empty_is_reported() -> None:
    report = VALID_REPORT + (
        "\n## Traceability Matrix\n\n"
        "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |\n"
        "|---|-----|----------|-------|-------|-------------------|--------|--------|\n"
    )
    assert "MD.matrix_empty" in _rules(_lint_with_matrix(report))


# --- §7.9: the parser is shared -----------------------------------------------


def test_no_hand_rolled_row_parsing_remains_in_the_contracts() -> None:
    """§7.9's last acceptance bullet. Both phase contracts must go through the
    shared parser — a second row grammar is how the two sides drifted before."""
    from pathlib import Path as _P

    root = _P(__file__).resolve().parents[1] / "spec_linter" / "contracts"
    for name in ("build_report.py", "design_phase.py"):
        source = (root / name).read_text()
        assert 'strip("|").split("|")' not in source, f"{name} still splits cells by hand"
        assert "_NUMBERED_ROW" not in source, f"{name} still has its own row regex"


# --- round-1 review fixes (PR B) ----------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "| # | Level | Description | Location | State |",
        "| # | Impact | Description | Location | Resolution |",
        "| # | Criticality | Description | Location | Outcome |",
    ],
)
def test_synonym_column_names_still_identify_a_findings_table(header: str) -> None:
    """Review finding 1 (Critical): a findings table whose columns use a
    sanctioned synonym must still be recognised — recognition is by the closed
    COLUMN vocabulary, which is contract data and extensible by one line."""
    block = _SEVER + f"{header}\n|---|---|---|---|---|\n| 1 | Critical | SQLi | db.py | OPEN |\n"
    assert lint(_sever(block, moved=True), _real_contract()).level == Level.FAIL


def test_prose_fragment_mentioning_critical_is_not_a_finding() -> None:
    """Review finding 2: inheritance is POSITIONAL. A stray one-cell line that
    merely contains the word is prose, not a severed findings row."""
    report = _sever("\n\n| this dependency is critical for phase 2, tracked separately |")
    assert "BR.open_blocking_finding" not in _rules(lint(report, _real_contract()))


def test_decision_table_saying_important_is_not_a_finding() -> None:
    """The cry-wolf guard that killed the content-based recognition attempt:
    a legitimate table may simply CONTAIN a severity word."""
    report = VALID_REPORT + (
        "\n## Autonomous Decisions\n\n"
        "| # | Decision Point | Options Considered | Chose | Rationale |\n"
        "|---|----------------|--------------------|-------|-----------|\n"
        "| 1 | Important | A vs B | A | deferred to a follow-up |\n"
    )
    assert "BR.open_blocking_finding" not in _rules(_lint(report))


def test_a_dash_row_cannot_turn_a_finding_into_a_header() -> None:
    """Review finding 5, end to end: the simplest bypass found in this PR —
    a blank line plus a dash row, no boundary trick required."""
    report = _sever("\n\n| 2 | Critical | SQL injection | db.py:42 |  |\n| - | - | - | - | - |")
    verdict = lint(report, _real_contract())
    assert verdict.level == Level.FAIL
    assert "BR.open_blocking_finding" in _rules(verdict)


# --- review finding 7: the ambiguity is closed at EVERY surface ---------------


def test_dash_row_cannot_hide_an_uncovered_must_in_the_matrix() -> None:
    report = VALID_REPORT + (
        "\n## Traceability Matrix\n\n"
        "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |\n"
        "|---|-----|----------|-------|-------|-------------------|--------|--------|\n"
        "| 1 | REQ-1 | MUST | TASK-A | tests/a.py | unit | Pass | clean |\n\n"
        "| 2 | REQ-2 | MUST | TASK-B |  |  |  |  |\n"
        "| - | - | - | - | - | - | - | - |\n"
    )
    rules = _rules(_lint_with_matrix(report))
    assert "BR.must_uncovered" in rules
    assert "MD.table_malformed" in rules


def test_dash_row_cannot_hide_a_dirty_task_review() -> None:
    report = _report_with_task_ids(VALID_REPORT, "TASK-1", "TASK-2") + (
        "\n## Task Reviews\n\n"
        "| # | Task ID | Risk | Reviewer | Verdict |\n"
        "|---|---------|------|----------|---------|\n"
        "| 1 | TASK-1 | low | @r | clean |\n\n"
        "| 2 | TASK-2 | low | @r | dirty |\n"
        "| - | - | - | - | - |\n"
    )
    assert "BR.task_review_dirty" in _rules(_lint_with_task_review(report))
