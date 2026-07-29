"""Doc-contract tests for the RISK_PROFILES feature.

Pins the top-level `risk_profiles` block in WORKFLOW_CONTRACTS.yaml (levels,
dimensions, dimension_values, elevation_rules, override invariant, legacy
default), the define phase's deliberate non-extension of
`required_sections` (Observe/Warn: Enforce deferred), the DEFINE template's
Risk Profile YAML section, the sdd-define skill's derivation step, the
DESIGN template's and sdd-design skill's Risk Level echo (never
recomputed), the BUILD_REPORT template's Risk Level row, the version
history entry, and the spec-linter's `DefinePhaseContract` / `RP.*` rules
documented in USAGE.md. These are documentation contracts, not runtime
behavior -- each test asserts that a fact stated in one file is still
present, so the contract can't silently drift.
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
SPEC_LINTER_USAGE = ROOT / "tools/spec-linter/USAGE.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_risk_profiles_block_registered():
    risk_profiles = contracts()["risk_profiles"]
    assert risk_profiles["rollout"] == "observe_warn"
    assert risk_profiles["levels"] == ["low", "medium", "high", "critical"]
    assert risk_profiles["dimensions"] == [
        "data_loss",
        "security",
        "reversibility",
        "blast_radius",
        "migration",
    ]
    assert risk_profiles["dimension_values"] == [
        "none",
        "low",
        "medium",
        "high",
        "critical",
    ]


def test_elevation_rules_are_data():
    elevation_rules = contracts()["risk_profiles"]["elevation_rules"]
    assert len(elevation_rules) >= 5
    assert all(isinstance(rule["trigger"], str) for rule in elevation_rules)

    floors = {
        rule["trigger"]: rule["floor"]
        for rule in elevation_rules
        if "floor" in rule
    }
    assert floors["authentication or authorization change"] == "high"
    assert floors["destructive migration"] == "critical"
    assert floors["production write without rollback"] == "critical"
    assert floors["new endpoint without sensitive data"] == "medium"

    assert any(rule.get("typical") == "low" for rule in elevation_rules)


def test_override_invariant_preserves_critical_halt():
    override = contracts()["risk_profiles"]["override"]
    assert override["required_fields"] == ["author", "rationale"]
    assert "CRITICAL halt" in override["invariant"]


def test_legacy_default_is_medium_warn_never_silent_low():
    legacy = contracts()["risk_profiles"]["legacy"]
    assert legacy["effective_level"] == "medium"
    assert legacy["mode"] == "WARN"


def test_define_required_sections_not_extended():
    assert "risk_profile" not in contracts()["define"]["required_sections"]


def test_define_template_carries_risk_profile_section():
    text = DEFINE_TEMPLATE.read_text()
    assert "## Risk Profile" in text
    assert "risk_profile:" in text
    assert "override:" in text


def test_define_skill_derives_profile():
    text = DEFINE_SKILL.read_text()
    assert "Step 5.5: Derive the Risk Profile" in text
    assert "max(dimension values)" in text
    assert "never a silent" in text


def test_design_template_and_skill_echo_level():
    assert "**Risk Level**" in DESIGN_TEMPLATE.read_text()
    text = DESIGN_SKILL.read_text()
    assert "Risk profile echo" in text
    assert "never recomputed" in text


def test_build_report_template_carries_risk_level_row():
    assert "**Risk Level**" in BUILD_REPORT_TEMPLATE.read_text()


def test_version_history_records_risk_profiles():
    version_history = contracts()["version_history"]
    assert any(
        "RISK_PROFILES" in change
        for entry in version_history
        for change in entry["changes"]
    )


def test_usage_documents_define_phase_risk_rules():
    text = SPEC_LINTER_USAGE.read_text()
    assert "DefinePhaseContract" in text
    assert "RP.*" in text
