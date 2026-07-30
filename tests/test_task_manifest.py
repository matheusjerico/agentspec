"""Doc-contract tests for the TASK_MANIFEST feature.

Pins the top-level `task_manifest` block in WORKFLOW_CONTRACTS.yaml
(manifest_version, required task fields, files keys, verification keys,
blocking vs. advisory rules as data, the opt-in v1-silent adoption
invariant, and the write_conflict definition), the DESIGN template's
Task Manifest (v2) section, the sdd-design skill's task derivation step,
the sdd-build skill's v2-graph-consuming / v1-inference-fallback branches,
the BUILD_REPORT template's Task ID column, the version history entry,
the spec-linter's `DesignPhaseContract` / `TM.*` rules documented in
USAGE.md, and the design phase's deliberate non-extension of
`required_sections` (the manifest stays opt-in, never required). These
are documentation contracts, not runtime behavior -- each test asserts
that a fact stated in one file is still present, so the contract can't
silently drift.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
DESIGN_TEMPLATE = ROOT / ".claude/sdd/templates/DESIGN_TEMPLATE.md"
DESIGN_SKILL = ROOT / ".claude/skills/sdd-design/SKILL.md"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
BUILD_REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
SPEC_LINTER_USAGE = ROOT / "tools/spec-linter/USAGE.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_task_manifest_block_registered():
    task_manifest = contracts()["task_manifest"]
    assert task_manifest["manifest_version"] == 2
    assert task_manifest["required_task_fields"] == [
        "id",
        "title",
        "files",
        "verification",
    ]
    assert task_manifest["files_keys"] == ["create", "modify", "tests"]
    assert task_manifest["verification_keys"] == ["red", "green", "regression"]


def test_blocking_and_advisory_rules_are_data():
    rules = contracts()["task_manifest"]["rules"]
    assert rules["blocking"] == [
        "unparseable",
        "duplicate_id",
        "cycle",
        "unknown_dependency",
        "write_conflict",
        "missing_verification",
    ]
    assert rules["advisory"] == ["missing_requirements"]


def test_adoption_requires_new_artifacts_and_names_legacy_adapter():
    task_manifest = contracts()["task_manifest"]
    assert "new artifacts: required" in task_manifest["adoption"]
    assert "legacy" in task_manifest["adoption"]
    assert "parallel_group" in task_manifest["write_conflict"]


def test_design_template_carries_task_manifest_section():
    text = DESIGN_TEMPLATE.read_text()
    assert "## Task Manifest (v2)" in text
    assert "manifest_version: 2" in text
    assert "depends_on" in text


def test_design_skill_derives_tasks():
    text = DESIGN_SKILL.read_text()
    assert "Step 4.7: Derive the Task Manifest (v2)" in text
    assert "verifiable change" in text
    assert "Size budget" in text


def test_build_skill_consumes_v2_graph():
    text = BUILD_SKILL.read_text()
    assert "manifest_version: 2" in text
    assert "NO inference" in text
    assert "topological order" in text
    assert "manifest_version: 1" in text


def test_build_report_template_carries_task_id_column():
    text = BUILD_REPORT_TEMPLATE.read_text()
    assert "| # | Task ID | Task |" in text
    assert "**Manifest:**" in text


def test_version_history_records_task_manifest():
    version_history = contracts()["version_history"]
    assert any(
        "TASK_MANIFEST" in change
        for entry in version_history
        for change in entry["changes"]
    )


def test_usage_documents_design_phase_tm_rules():
    text = SPEC_LINTER_USAGE.read_text()
    assert "DesignPhaseContract" in text
    assert "TM.*" in text


def test_design_required_sections_not_extended():
    assert "task_manifest" not in contracts()["design"]["required_sections"]
