"""Doc-contract tests for the TASK_REVIEW feature (Increment 5).

Pins the top-level `task_review` block in WORKFLOW_CONTRACTS.yaml (verdict
vocabulary, the risk-keyed `policy_by_risk` map, the blind-first rule,
`fix_budget_per_task` (kept distinct from the whole-branch final review's
`fix_loop_budget`), `dependents_blocked_on`, and the enforcement map read by
the CLI), the invariant that the whole-branch final review
(`build.execution.final_review`) is never replaced by per-task reviews and
remains byte-identical to its pre-Increment-5 shape, the sdd-build skill's
ownership of Step 4.6 (blind-first per-task review dispatch), the
BUILD_REPORT template's Task Reviews section, the spec-linter's
`BR.task_review_missing` / `BR.task_review_dirty` rules documented in
USAGE.md, and the version history entry. These are documentation contracts,
not runtime behavior -- each test asserts that a fact stated in one file is
still present, so the contract can't silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
BUILD_REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
SPEC_LINTER_USAGE = ROOT / "tools/spec-linter/USAGE.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_task_review_block_registered():
    task_review = contracts()["task_review"]
    assert task_review["verdicts"] == [
        "clean",
        "clean-with-minors",
        "dirty",
        "skipped-by-policy",
    ]
    assert task_review["fix_budget_per_task"] == 1
    assert task_review["dependents_blocked_on"] == ["dirty"]


def test_policy_by_risk_is_data():
    policy_by_risk = contracts()["task_review"]["policy_by_risk"]
    assert policy_by_risk == {
        "low": "executor_checklist",
        "medium": "selective_independent",
        "high": "independent_required",
        "critical": "independent_plus_specialist",
    }


def test_blind_first_rule_recorded():
    blind_first = contracts()["task_review"]["blind_first"]
    assert "WITHOUT the implementer's rationale" in blind_first


def test_enforcement_map():
    enforcement = contracts()["task_review"]["enforcement"]
    assert enforcement["high_critical_missing"] == "FAIL"
    assert enforcement["medium_missing"] == "WARN"
    assert enforcement["low_missing"] == "silent"
    assert enforcement["no_risk_row"] == "silent"
    assert enforcement["dirty_verdict"] == "FAIL"


def test_final_review_invariant_recorded_and_untouched():
    task_review = contracts()["task_review"]
    assert "final review" in task_review["invariant"]
    assert "never replace" in task_review["invariant"]

    final_review = contracts()["build"]["execution"]["final_review"]
    assert final_review["fix_loop_budget"] == 2
    assert final_review["verdicts"] == ["clean", "clean-with-minors", "dirty", "missing"]


def test_budget_separation():
    task_review_budget = contracts()["task_review"]["fix_budget_per_task"]
    final_review_budget = contracts()["build"]["execution"]["final_review"]["fix_loop_budget"]
    assert task_review_budget == 1
    assert final_review_budget == 2
    assert task_review_budget != final_review_budget


def test_build_skill_owns_step_4_6():
    text = BUILD_SKILL.read_text()
    normalized = " ".join(text.split())
    assert "Step 4.6: Per-Task Review" in text
    assert "blind-first" in normalized.lower()
    assert "dependents DO NOT start" in normalized
    assert "never replace" in text


def test_build_report_template_carries_task_reviews_section():
    text = BUILD_REPORT_TEMPLATE.read_text()
    assert "## Task Reviews" in text
    assert "| # | Task ID | Risk | Reviewer | Verdict |" in text


def test_usage_documents_task_review_rules():
    text = SPEC_LINTER_USAGE.read_text()
    assert "BR.task_review_missing" in text
    assert "BR.task_review_dirty" in text


def test_version_history_records_task_review():
    version_history = contracts()["version_history"]
    assert any(
        "TASK_REVIEW (Increment 5)" in change
        for entry in version_history
        for change in entry["changes"]
    )
