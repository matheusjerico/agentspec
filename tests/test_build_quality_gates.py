"""Doc-contract tests for the BUILD_QUALITY_GATES feature.

Pins the whole-branch adversarial review (sdd-build Step 5.5), the pre-ship
review-verdict gate, the BUILD_REPORT Review Verdict / TDD Evidence
sections, and the `--tdd` opt-in flag across the artifacts that declare
them: WORKFLOW_CONTRACTS.yaml, the build/ship/autopilot skills, the
BUILD_REPORT template, and the /build command. These are documentation
contracts, not runtime behavior -- each test asserts that a fact stated in
one file is still present, so the contract can't silently drift.
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


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_final_review_block_registered():
    review = contracts()["build"]["execution"]["final_review"]
    assert review["reviewer"] == "code-reviewer"
    assert review["fix_loop_budget"] == 2
    assert review["verdicts"] == ["clean", "clean-with-minors", "dirty", "missing"]


def test_pre_ship_checklist_has_five_items_ending_in_review_verdict():
    checklist = contracts()["ship"]["pre_ship_checklist"]
    assert len(checklist) == 5
    assert checklist[-1] == "review_verdict_clean"


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
    assert "all 5 items" in text


def test_build_command_documents_tdd_flag():
    assert "--tdd" in BUILD_COMMAND.read_text()
