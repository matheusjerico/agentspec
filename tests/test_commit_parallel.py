"""Doc-contract tests for the COMMIT_PARALLEL_POLICY feature (Increment 7).

Pins the top-level `commit_parallel` block in WORKFLOW_CONTRACTS.yaml (the
5 commit rules as data, the commit_recording vocabulary — sha/unavailable/
session, Git absence never a blocker — the 5 parallel preconditions, and the
serialize-on-conflict policy), sdd-build's Step 4.9 (per-task commit into
the report's Commit column, plus the parallel dispatch policy), the
BUILD_REPORT template's new Commit column, sdd-autopilot's note that
per-task commits compose with the phase checkpoint, and the version history
entry. These are documentation contracts, not runtime behavior -- each test
asserts that a fact stated in one file is still present, so the contract
can't silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
BUILD_REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
AUTOPILOT_SKILL = ROOT / ".claude/skills/sdd-autopilot/SKILL.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_commit_parallel_block_registered():
    commit_parallel = contracts()["commit_parallel"]
    commit_rules = commit_parallel["commit_rules"]
    assert len(commit_rules) == 5

    joined = " ".join(commit_rules)
    assert "Conventional Commits" in joined
    assert "never mix" in joined
    assert "RED commit" in joined
    assert "rewrite history" in joined
    assert "maintainer" in joined


def test_commit_recording_vocabulary():
    commit_recording = contracts()["commit_parallel"]["commit_recording"]
    assert commit_recording["vocabulary"] == ["sha", "unavailable", "session"]
    assert "never a blocker" in commit_recording["unavailable"]


def test_parallel_preconditions_five():
    parallel_preconditions = contracts()["commit_parallel"]["parallel_preconditions"]
    assert len(parallel_preconditions) == 5

    joined = " ".join(parallel_preconditions)
    assert "dependencies complete" in joined
    assert "disjoint" in joined
    assert "migration" in joined
    assert "budget" in joined
    assert "merge strategy" in joined


def test_on_conflict_serializes():
    on_conflict = contracts()["commit_parallel"]["on_conflict"]
    assert "serialize" in on_conflict
    assert "never" in on_conflict


def test_build_skill_owns_step_4_9():
    text = BUILD_SKILL.read_text()
    assert "Step 4.9: Commit the Task" in text
    assert "execution.commit" in text
    assert "unavailable" in text
    assert "Parallel dispatch" in text


def test_build_skill_serialize_on_conflict():
    text = BUILD_SKILL.read_text()
    assert "serializes the remainder" in text
    assert "never an automatic risky merge" in text


def test_build_report_template_carries_commit_column():
    text = BUILD_REPORT_TEMPLATE.read_text()
    assert "| # | Task ID | Task | Agent | Status | Commit |" in text
    assert "unavailable" in text


def test_autopilot_composes_task_commits():
    text = AUTOPILOT_SKILL.read_text()
    normalized = " ".join(text.split())
    assert "Per-task commits" in normalized
    assert "checkpoint" in normalized
    assert "agent" in normalized
    assert "budget" in normalized


def test_version_history_records_commit_parallel():
    version_history = contracts()["version_history"]
    assert any(
        "COMMIT_PARALLEL_POLICY (Increment 7)" in change
        for entry in version_history
        for change in entry["changes"]
    )


def test_build_skill_records_sha_linkage() -> None:
    text = BUILD_SKILL.read_text()
    normalized = " ".join(text.split())
    assert "short SHA" in normalized
    assert "Commit column" in normalized


def test_build_skill_red_commit_grammar() -> None:
    text = BUILD_SKILL.read_text()
    assert "test(red): <task-id>" in text
    assert "unmarked failing-test commits" in " ".join(text.split())
