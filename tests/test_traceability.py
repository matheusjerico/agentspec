"""Doc-contract tests for the TRACEABILITY_MATRIX feature (Increment 6).

Pins the top-level `traceability` block in WORKFLOW_CONTRACTS.yaml (the
10-type verification vocabulary, the REQ-ID grammar, the `coverage_rules`
map, the 5-row frontend/browser policy, and the enforcement map read by the
spec-linter), the DEFINE template's/skill's REQ-ID assignment in the Goals
table (never renumbered on iteration), the DESIGN template's/skill's
generation of the Traceability Matrix section (Step 4.8, frontend/browser
policy), the BUILD_REPORT template's/skill's filling of that matrix
(+Result/+Review columns, `BR.must_uncovered`), the spec-linter's
`TX.must_without_task` / `BR.must_uncovered` / `BR.matrix_missing` rules
documented in USAGE.md, and the version history entry. These are
documentation contracts, not runtime behavior -- each test asserts that a
fact stated in one file is still present, so the contract can't silently
drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
DEFINE_TEMPLATE = ROOT / ".claude/sdd/templates/DEFINE_TEMPLATE.md"
DEFINE_SKILL = ROOT / ".claude/skills/sdd-define/SKILL.md"
DESIGN_TEMPLATE = ROOT / ".claude/sdd/templates/DESIGN_TEMPLATE.md"
DESIGN_SKILL = ROOT / ".claude/skills/sdd-design/SKILL.md"
BUILD_REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
SPEC_LINTER_USAGE = ROOT / "tools/spec-linter/USAGE.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_traceability_block_registered():
    traceability = contracts()["traceability"]
    assert traceability["verification_types"] == [
        "unit",
        "integration",
        "contract",
        "e2e",
        "browser_accessibility",
        "security",
        "migration_rollback",
        "data_quality",
        "observability",
        "deterministic_inspection",
    ]
    grammar = traceability["requirement_id_grammar"]
    assert "REQ-" in grammar
    assert "never orphan-flagged" in grammar


def test_coverage_rules_are_data():
    coverage_rules = contracts()["traceability"]["coverage_rules"]
    assert "FAIL at Design" in coverage_rules["must_without_task"]
    assert "exception:" in coverage_rules["must_uncovered_at_build"]
    assert "deferred" in coverage_rules["should_deferred"]
    assert "revision history" in coverage_rules["could_removed"]


def test_frontend_policy_five_rows():
    frontend_policy = contracts()["traceability"]["frontend_policy"]
    required_rows = frontend_policy["required_rows"]
    assert len(required_rows) == 5

    joined = " ".join(required_rows).lower()
    assert "e2e" in joined
    assert "accessibility" in joined
    assert "timezone" in joined
    assert "state" in joined


def test_enforcement_map():
    enforcement = contracts()["traceability"]["enforcement"]
    assert enforcement["design_must_without_task"] == "FAIL"
    assert enforcement["design_unknown_type"] == "FAIL"
    assert enforcement["design_orphan_reference"] == "WARN"
    assert enforcement["build_must_uncovered"] == "FAIL"
    assert enforcement["build_matrix_missing_high_critical"] == "WARN"
    assert enforcement["build_matrix_missing_medium_low"] == "silent"


def test_define_template_carries_req_id_column():
    text = DEFINE_TEMPLATE.read_text()
    assert "| ID | Priority | Goal |" in text
    assert "REQ-001" in text
    assert "Never renumber" in text


def test_define_skill_assigns_req_ids():
    text = DEFINE_SKILL.read_text()
    normalized = " ".join(text.split())
    assert "REQ-001" in normalized
    assert "Never renumber" in normalized


def test_design_template_and_skill_carry_matrix():
    template_text = DESIGN_TEMPLATE.read_text()
    assert "## Traceability Matrix" in template_text
    assert "| # | REQ | Priority | Tasks | Tests | Verification Type |" in template_text

    skill_text = DESIGN_SKILL.read_text()
    assert "Step 4.8: Generate the Traceability Matrix" in skill_text
    assert "Frontend/browser policy" in skill_text


def test_build_template_and_skill_fill_matrix():
    template_text = BUILD_REPORT_TEMPLATE.read_text()
    assert "## Traceability Matrix" in template_text
    assert "| Result | Review |" in template_text

    skill_text = BUILD_SKILL.read_text()
    assert "Fill the Traceability Matrix" in skill_text
    assert "BR.must_uncovered" in skill_text


def test_usage_documents_matrix_rules():
    text = SPEC_LINTER_USAGE.read_text()
    assert "TX.must_without_task" in text
    assert "BR.must_uncovered" in text
    assert "BR.matrix_missing" in text


def test_version_history_records_traceability():
    version_history = contracts()["version_history"]
    assert any(
        "TRACEABILITY_MATRIX (Increment 6)" in change
        for entry in version_history
        for change in entry["changes"]
    )
