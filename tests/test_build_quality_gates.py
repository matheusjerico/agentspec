"""Doc-contract tests for the BUILD_QUALITY_GATES feature.

Pins the whole-branch adversarial review (sdd-build Step 5.5), the pre-ship
review-verdict gate, the BUILD_REPORT Review Verdict / TDD Evidence
sections, the `--tdd` opt-in flag, and the BUILD_REPORT_CONTRACT_ENFORCEMENT
phase contract (build required_sections, report_contract, the Build
consumer binding, sdd-build Step 6.5 / sdd-ship's re-validation, autopilot's
fail-closed lint, and the plugin-build test split) across the artifacts
that declare them: WORKFLOW_CONTRACTS.yaml, the build/ship/autopilot
skills, the BUILD_REPORT template, the /build command, and
build-plugin.sh. These are documentation contracts, not runtime behavior --
each test asserts that a fact stated in one file is still present, so the
contract can't silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
SHIP_SKILL = ROOT / ".claude/skills/sdd-ship/SKILL.md"
AUTOPILOT_SKILL = ROOT / ".claude/skills/sdd-autopilot/SKILL.md"
REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
BUILD_COMMAND = ROOT / ".claude/commands/workflow/build.md"
BUILD_PLUGIN_SCRIPT = ROOT / "build-plugin.sh"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_final_review_block_registered():
    review = contracts()["build"]["execution"]["final_review"]
    assert review["reviewer"] == "code-reviewer"
    assert review["fix_loop_budget"] == 2
    assert review["verdicts"] == ["clean", "clean-with-minors", "dirty", "missing"]


def test_pre_ship_checklist_has_six_items_ending_in_contract_gate():
    checklist = contracts()["ship"]["pre_ship_checklist"]
    assert len(checklist) == 6
    assert checklist[-2] == "review_verdict_clean"
    assert checklist[-1] == "build_report_contract_gate_pass"


def test_build_report_template_carries_review_verdict_section():
    text = REPORT_TEMPLATE.read_text()
    assert "## Review Verdict" in text
    assert "## TDD Evidence" in text


def test_build_skill_defines_step_5_5_and_tdd_mode():
    text = BUILD_SKILL.read_text()
    assert "Step 5.5: Whole-Branch Adversarial Review" in text
    assert "--tdd" in text


def test_ship_skill_refuses_dirty_and_missing_verdicts():
    text = SHIP_SKILL.read_text()
    assert "Review Verdict is `dirty` or `missing`" in text
    assert "Review Verdict dirty or missing | 0.50 | Cannot ship" in text
    assert "Review Verdict is clean or clean-with-minors" in text


def test_fix_loop_budget_consistent_across_files():
    budget = contracts()["build"]["execution"]["final_review"]["fix_loop_budget"]
    assert f"budget {budget} rounds" in BUILD_SKILL.read_text()
    assert f"{budget} rounds per build" in AUTOPILOT_SKILL.read_text()
    assert f"{{0-{budget}}}/{budget}" in REPORT_TEMPLATE.read_text()


def test_autopilot_has_gate_r():
    text = AUTOPILOT_SKILL.read_text()
    assert "R — Review" in text
    assert "all 6 items" in text


def test_build_command_documents_tdd_flag():
    assert "--tdd" in BUILD_COMMAND.read_text()


def test_build_phase_has_required_sections_contract():
    assert contracts()["build"]["required_sections"] == [
        "metadata",
        "summary",
        "task_execution_with_agent_attribution",
        "files_created",
        "verification_results",
        "review_verdict",
        "acceptance_test_verification",
        "final_status",
    ]


def test_build_report_contract_block_registered():
    report_contract = contracts()["build"]["report_contract"]
    assert report_contract["schema_version"] == 2
    assert report_contract["tdd_mode_values"] == ["off", "opt-in", "required"]
    assert report_contract["legacy"]["manual"] == "WARN"
    assert report_contract["legacy"]["autopilot"] == "FAIL"


def test_build_consumer_binding_is_wired():
    bindings = contracts()["contract_enforcement"]["consumer_bindings"]["bindings"]
    build_binding = next(b for b in bindings if b["phase"] == "Build")
    assert build_binding["status"].startswith("wired")


def test_build_report_template_carries_contract_metadata_rows():
    text = REPORT_TEMPLATE.read_text()
    assert "**Schema Version** | 2" in text
    assert "**TDD Mode**" in text


def test_build_skill_defines_step_6_5_contract_gate():
    text = BUILD_SKILL.read_text()
    assert "Step 6.5: Contract Gate" in text
    assert "--phase build" in text


def test_ship_skill_revalidates_build_contract():
    assert "--phase build" in SHIP_SKILL.read_text()


def test_autopilot_lints_build_report_fail_closed():
    assert "--legacy-mode fail" in AUTOPILOT_SKILL.read_text()


def test_version_history_records_contract_enforcement():
    version_history = contracts()["version_history"]
    assert any(
        "BUILD_REPORT_CONTRACT_ENFORCEMENT" in change
        for entry in version_history
        for change in entry["changes"]
    )


def test_build_plugin_excludes_parity_from_prebuild_tests():
    text = BUILD_PLUGIN_SCRIPT.read_text()
    assert "--ignore=tests/test_plugin_parity.py" in text
    assert text.count("tests/test_plugin_parity.py") >= 2
