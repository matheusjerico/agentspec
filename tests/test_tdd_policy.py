"""Doc-contract tests for the RISK_DRIVEN_TDD feature.

Pins the top-level `tdd_policy` block in WORKFLOW_CONTRACTS.yaml
(effective-mode rule -- strongest of --tdd flag, risk_policy[risk level],
any manifest task with execution.tdd == required -- the risk_policy map,
the --no-tdd flag's dispenses/requires/never constraints, the 5 sanctioned
exception_categories, the RED-validity statement, and the enforcement map
read by the CLI), the sdd-build skill's ownership of effective-mode
derivation and RED validity, the /build command's documentation of
--no-tdd, the BUILD_REPORT template's exception grammar, the spec-linter's
`BR.tdd_required_by_risk` / `BR.tdd_exception_invalid` rules documented in
USAGE.md, and the version history entry. These are documentation
contracts, not runtime behavior -- each test asserts that a fact stated in
one file is still present, so the contract can't silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
BUILD_COMMAND = ROOT / ".claude/commands/workflow/build.md"
BUILD_REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
SPEC_LINTER_USAGE = ROOT / "tools/spec-linter/USAGE.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_tdd_policy_block_registered():
    tdd_policy = contracts()["tdd_policy"]
    assert tdd_policy["risk_policy"] == {
        "low": "recommended",
        "medium": "required_for_logic",
        "high": "required",
        "critical": "required",
    }
    assert "--tdd" in tdd_policy["effective_mode_rule"]
    assert "execution.tdd" in tdd_policy["effective_mode_rule"]


def test_no_tdd_flag_constraints():
    no_tdd_flag = contracts()["tdd_policy"]["no_tdd_flag"]
    assert no_tdd_flag["dispenses"] == ["low", "medium"]
    assert no_tdd_flag["requires"] == "recorded_justification"
    assert no_tdd_flag["never"] == ["high", "critical"]


def test_exception_categories_are_data():
    exception_categories = contracts()["tdd_policy"]["exception_categories"]
    assert len(exception_categories) >= 5
    assert "non_executable_documentation" in exception_categories
    assert "declarative_configuration" in exception_categories


def test_enforcement_map_is_wired_semantics():
    tdd_policy = contracts()["tdd_policy"]
    enforcement = tdd_policy["enforcement"]
    assert enforcement["high_critical_off"] == "FAIL"
    assert enforcement["medium_off"] == "FAIL"
    assert enforcement["low_off"] == "silent"
    assert enforcement["no_risk_row"] == "silent"
    assert "pre-existing failure" in tdd_policy["red_validity"]


def test_build_skill_owns_effective_mode_and_no_tdd():
    text = BUILD_SKILL.read_text()
    assert "TDD mode (risk-driven policy" in text
    assert "--no-tdd" in text
    assert "RED validity" in text
    assert "exception: <category>" in text


def test_build_command_documents_no_tdd_flag():
    text = BUILD_COMMAND.read_text()
    assert "--no-tdd" in text
    assert "refused" in text


def test_build_report_template_documents_exception_grammar():
    text = BUILD_REPORT_TEMPLATE.read_text()
    assert "exception: <category>" in text
    assert "tdd_policy.exception_categories" in text


def test_usage_documents_tdd_rules():
    text = SPEC_LINTER_USAGE.read_text()
    assert "BR.tdd_required_by_risk" in text
    assert "BR.tdd_exception_invalid" in text


def test_version_history_records_risk_driven_tdd():
    version_history = contracts()["version_history"]
    assert any(
        "RISK_DRIVEN_TDD" in change
        for entry in version_history
        for change in entry["changes"]
    )
