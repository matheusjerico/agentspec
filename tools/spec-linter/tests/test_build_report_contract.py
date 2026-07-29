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
