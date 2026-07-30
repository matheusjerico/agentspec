"""Doc-contract tests for the WORKFLOW_METRICS feature (Increment 9).

Pins the top-level `workflow_metrics` block in WORKFLOW_CONTRACTS.yaml
(schema_version 1, the closed 13-key catalog, the availability rule, the
per-consumer behavior), the BUILD_REPORT_TEMPLATE's Workflow Metrics section,
sdd-build's measured-only emission conduct, sdd-ship's summary step with the
no-adaptive-automation boundary, the version history entry, and the AT-009
comparability property (two same-version blocks diff key-by-key without
prose). These are documentation contracts, not runtime behavior -- each test
asserts that a fact stated in one file is still present, so the contract
can't silently drift. The runtime rules themselves (BR.metrics_*) are unit
tested in tools/spec-linter/tests/test_metrics_rules.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
SHIP_SKILL = ROOT / ".claude/skills/sdd-ship/SKILL.md"

CATALOG = [
    "feature",
    "phase_duration_seconds",
    "time_to_first_green_seconds",
    "task_count",
    "effective_parallelism",
    "tests_by_type",
    "reopened_tasks",
    "fix_rounds",
    "findings",
    "requirements",
    "operational_skips",
    "risk_overrides",
    "tokens_cost",
]


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def _template_block() -> dict:
    text = REPORT_TEMPLATE.read_text()
    section = text.split("## Workflow Metrics", 1)[1]
    fence = re.search(r"```yaml\s*\n(.*?)```", section, re.DOTALL)
    assert fence is not None, "template section lost its yaml fence"
    # Neutralize {PLACEHOLDER} tokens for parsing only — they never contain a
    # colon, so yaml flow mappings like `{ build: 0 }` are left intact; the
    # shape (keys, nesting) is what this test pins.
    skeleton = re.sub(r"\{[^{}:]*\}", "X", fence.group(1))
    return yaml.safe_load(skeleton)["workflow_metrics"]


def test_workflow_metrics_block_registered():
    block = contracts()["workflow_metrics"]
    assert block["schema_version"] == 1
    assert block["catalog"] == CATALOG


def test_availability_rule_forbids_estimates():
    rule = contracts()["workflow_metrics"]["availability_rule"]
    assert "{value: null, reason: <why>}" in rule
    assert "never estimated" in rule
    assert "reliably" in rule  # tokens/cost only when the platform is reliable


def test_behavior_names_both_consumers():
    behavior = contracts()["workflow_metrics"]["behavior"]
    assert "measured values only" in behavior["build"]
    assert "BR.metrics_" in behavior["build"]
    assert "NEVER auto-change policies" in behavior["ship"]
    assert "human review" in behavior["ship"]


def test_template_section_carries_the_full_catalog():
    block = _template_block()
    assert block["schema_version"] == 1
    assert set(block.keys()) == set(CATALOG) | {"schema_version"}


def test_template_skeleton_models_the_availability_mapping():
    block = _template_block()
    unmeasured = block["time_to_first_green_seconds"]
    assert unmeasured["value"] is None
    assert "reason" in unmeasured


def test_build_skill_emission_conduct():
    # Whitespace-normalized: skill prose hard-wraps mid-phrase.
    text = " ".join(BUILD_SKILL.read_text().split())
    assert "Emit the workflow_metrics block" in text
    assert "MEASURED values only" in text
    assert "forbidden conduct" in text  # estimating / interpolating / copying
    assert "honest null beats a plausible guess" in text


def test_ship_skill_summary_and_boundary():
    text = " ".join(SHIP_SKILL.read_text().split())
    assert "## Summarize workflow metrics" in text
    assert "never backfilled at ship time" in text
    assert "metrics NEVER auto-change policies" in text
    assert "multiple comparable runs AND human review" in text


def test_version_history_entry():
    entries = contracts()["version_history"]
    expected = ["3.20.0", "3.19.0", "3.18.0", "3.17.0", "3.16.0"]
    assert [entry["version"] for entry in entries[:5]] == expected
    assert "FAIL_CLOSED_TABLES" in entries[0]["changes"][0]
    assert "parse-never-filter" in entries[0]["changes"][0]
    assert "fix_rounds_override" in entries[1]["changes"][0]
    assert "MD.duplicate_contract_section" in entries[2]["changes"][0]
    assert "LINTER_FAIL_CLOSED" in entries[3]["changes"][0]
    assert "WORKFLOW_METRICS" in entries[4]["changes"][0]


def test_two_same_version_blocks_compare_without_prose():
    # AT-009: the comparability property — two valid blocks with the same
    # schema_version diff key-by-key with plain data access, no prose parsing.
    run_a = _template_block()
    run_b = {**run_a, "fix_rounds": {"local": 2, "final": 1}, "task_count": 6}
    assert run_a["schema_version"] == run_b["schema_version"]
    deltas = {k: (run_a[k], run_b[k]) for k in CATALOG if run_a[k] != run_b[k]}
    assert set(deltas) == {"fix_rounds", "task_count"}


def test_contract_gate_arms_metrics_from_the_real_contracts_file():
    # The CLI arms BR.metrics_* whenever the top-level block is a dict —
    # this repo's own contracts file must therefore arm it (dogfood).
    assert isinstance(contracts().get("workflow_metrics"), dict)
