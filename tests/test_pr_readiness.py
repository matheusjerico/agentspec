"""Doc-contract tests for the PR_READINESS feature (Increment 8).

Pins the top-level `pr_readiness` block in WORKFLOW_CONTRACTS.yaml (shared by
Build, Ship and /create-pr — 5 dimensions, 13 items, each mapped to an
evidence source with a `mutable` flag, plus the behavior vocabulary for each
consumer), the PR_READY_TEMPLATE.md shape Ship writes, sdd-ship's non-blocking
generation of the artifact, /create-pr's consumption/revalidation/publication
guard, sdd-build's PR boundary, sdd-autopilot's PR stage note, and the version
history entry. These are documentation contracts, not runtime behavior --
each test asserts that a fact stated in one file is still present, so the
contract can't silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
PR_READY_TEMPLATE = ROOT / ".claude/sdd/templates/PR_READY_TEMPLATE.md"
SHIP_SKILL = ROOT / ".claude/skills/sdd-ship/SKILL.md"
CREATE_PR_COMMAND = ROOT / ".claude/commands/workflow/create-pr.md"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
AUTOPILOT_SKILL = ROOT / ".claude/skills/sdd-autopilot/SKILL.md"

DIMENSIONS = ["branch", "quality", "traceability", "review", "delivery"]


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_pr_readiness_block_registered():
    pr_readiness = contracts()["pr_readiness"]
    assert pr_readiness["shared_by"] == ["build", "ship", "create-pr"]

    for dimension in DIMENSIONS:
        assert dimension in pr_readiness

    total_items = sum(len(pr_readiness[dimension]) for dimension in DIMENSIONS)
    assert total_items == 13


def test_every_item_evidence_mapped():
    pr_readiness = contracts()["pr_readiness"]
    for dimension in DIMENSIONS:
        for item_name, item in pr_readiness[dimension].items():
            assert isinstance(item["evidence"], str) and item["evidence"], (
                f"{dimension}.{item_name} missing evidence string"
            )
            assert isinstance(item["mutable"], bool), (
                f"{dimension}.{item_name} mutable flag is not a bool"
            )


def test_mutable_split():
    pr_readiness = contracts()["pr_readiness"]

    mutable_items = []
    frozen_items = []
    for dimension in DIMENSIONS:
        for item_name, item in pr_readiness[dimension].items():
            full_name = f"{dimension}.{item_name}"
            (mutable_items if item["mutable"] else frozen_items).append(full_name)

    expected_mutable = {
        "branch.working_tree_clean",
        "branch.base_resolved",
        "quality.tests",
        "quality.build",
        "review.verdict_unchanged",
    }
    assert set(mutable_items) == expected_mutable
    assert len(mutable_items) == 5
    assert len(frozen_items) == 8


def test_behavior_contract():
    behavior = contracts()["pr_readiness"]["behavior"]

    assert "never opens PRs" in behavior["build"]

    assert "PR_READY" in behavior["ship"]
    assert "non-destructive" in behavior["ship"]

    assert "revalidates" in behavior["create_pr"]
    assert "explicit user intent" in behavior["create_pr"]
    assert "legacy conduct" in behavior["create_pr"]


def test_pr_ready_template_shape():
    text = PR_READY_TEMPLATE.read_text()
    for fragment in [
        "## Readiness Checklist",
        "## PR Description (generated",
        "### Traceability Matrix (summarized)",
        "### Residual risks",
        "### Migration & rollback",
        "### Validation instructions",
        "## Gaps",
        "Delete this file once the PR URL exists",
    ]:
        assert fragment in text, f"missing: {fragment!r}"


def test_ship_skill_generates_pr_ready():
    text = SHIP_SKILL.read_text()
    normalized = " ".join(text.split())

    assert "PR_READY_{FEATURE}.md" in text
    assert "does NOT block the ship" in normalized
    assert "Gaps section" in normalized


def test_create_pr_consumes_and_revalidates():
    text = CREATE_PR_COMMAND.read_text()
    for fragment in [
        "PR_READY consumption",
        "Revalidate the MUTABLE subset",
        "never publish",
        "PASTED",
        "legacy conduct below applies unchanged",
    ]:
        assert fragment in text, f"missing: {fragment!r}"


def test_explicit_intent_guard():
    text = CREATE_PR_COMMAND.read_text()
    assert "explicit user intent" in text
    assert "Never open a PR as a side effect" in text


def test_build_boundary_and_autopilot_stage():
    build_text = BUILD_SKILL.read_text()
    normalized_build = " ".join(build_text.split())
    assert "never" in normalized_build
    assert "opens PRs" in normalized_build
    assert "never opens PRs" in normalized_build

    autopilot_text = AUTOPILOT_SKILL.read_text()
    assert "consuming the PR_READY artifact" in autopilot_text


def test_version_history_records_pr_readiness():
    version_history = contracts()["version_history"]
    assert any(
        "PR_READINESS (Increment 8)" in change
        for entry in version_history
        for change in entry["changes"]
    )


def test_pr_ready_template_checklist_has_ship_sha_anchor() -> None:
    text = PR_READY_TEMPLATE.read_text()
    assert "Ship HEAD SHA" in text
    assert "verdict_unchanged anchor" in text


def test_create_pr_skip_gate_over_legacy_steps() -> None:
    text = CREATE_PR_COMMAND.read_text()
    normalized = " ".join(text.split())
    assert "SKIP legacy Steps 1–5" in normalized or "SKIP legacy Steps 1-5" in normalized
    assert "resume the legacy flow at Step 6" in normalized
    assert "never guess" in normalized
