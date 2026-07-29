"""Tests for DefinePhaseContract, run through `engine.lint`.

One test per documented RP.* rule family (WARN + companion PASS forks) plus
the pre-existing L2.required_section FAIL semantics, built on a single
module-level VALID_DEFINE fixture — a minimal but fully conformant define doc
carrying a valid Risk Profile block — mutated per test via the `mutate`
helper so each test's intent (what changed, what should break) stays legible.

Rollout is `observe_warn`: every RP.* rule is Level.WARN, unconditionally — a
define doc can never FAIL on account of its Risk Profile, only on a missing
required section (L2.required_section, unchanged from SddPhaseContract).
"""

from __future__ import annotations

from spec_linter.contracts.define_phase import DefinePhaseContract
from spec_linter.engine import lint
from spec_linter.verdict import Level, Verdict

REQUIRED_SECTIONS = [
    "metadata",
    "problem_statement",
    "target_users",
    "goals",
    "success_criteria",
    "acceptance_tests",
    "out_of_scope",
    "constraints",
    "assumptions",
    "clarity_score_breakdown",
    "open_questions",
    "revision_history",
]
LEVELS = ["low", "medium", "high", "critical"]
DIMENSIONS = ["data_loss", "security", "reversibility", "blast_radius", "migration"]
DIMENSION_VALUES = ["none", "low", "medium", "high", "critical"]
OVERRIDE_REQUIRED = ["author", "rationale"]
LEGACY_LEVEL = "medium"


def _contract() -> DefinePhaseContract:
    return DefinePhaseContract(
        required_sections=REQUIRED_SECTIONS,
        levels=LEVELS,
        dimensions=DIMENSIONS,
        dimension_values=DIMENSION_VALUES,
        override_required=OVERRIDE_REQUIRED,
        legacy_level=LEGACY_LEVEL,
    )


def _lint(doc: str) -> Verdict:
    return lint(doc, _contract())


def _rules(verdict: Verdict) -> list[str]:
    return [f.rule for f in verdict.findings]


def mutate(report: str, old: str, new: str) -> str:
    """Replace `old` with `new`, asserting `old` is actually present in
    `report` — a guard against silently-green fixtures if VALID_DEFINE
    drifts and a mutation stops mutating anything."""
    assert old in report, f"fixture drift: {old!r} not found in report"
    return report.replace(old, new)


VALID_DEFINE = """\
# DEFINE: SAMPLE_FEATURE

## Metadata

| Field | Value |
|-------|-------|
| **Feature** | SAMPLE_FEATURE |
| **Status** | Ready for Design |
| **Date** | 2026-07-29 |

## Problem Statement

Users need a documented way to opt into a smaller feature.

## Target Users

Data engineers building pipelines who need clarity on scope.

## Goals

- MUST support X
- SHOULD support Y
- COULD support Z

## Success Criteria

- Feature ships with tests passing.

## Acceptance Tests

- Given valid input, when processed, then output matches spec.

## Out of Scope

- Multi-region support is out of scope for this iteration.

## Constraints

- Must run within existing CI budget.

## Risk Profile

> Derived in Phase 1 (sdd-define): level = max(dimension values), raised to
> any applicable elevation floor.

```yaml
risk_profile:
  level: medium
  reasons:
    - "sample reason for medium risk"
  dimensions:
    data_loss: medium
    security: medium
    reversibility: medium
    blast_radius: medium
    migration: medium
  override:
    applied: false
    author: null
    rationale: null
```

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Upstream data is UTF-8 | Would need re-encoding | [ ] |

## Clarity Score Breakdown

| Dimension | Score |
|-----------|-------|
| Problem | 3 |
| Users | 3 |
| Goals | 3 |
| Success | 3 |
| Scope | 3 |

## Open Questions

- None at this time.

## Revision History

| Date | Change |
|------|--------|
| 2026-07-29 | Initial draft |
"""


def test_valid_define_passes() -> None:
    verdict = _lint(VALID_DEFINE)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_missing_risk_profile_section_warns_profile_missing() -> None:
    start = VALID_DEFINE.index("## Risk Profile")
    end = VALID_DEFINE.index("## Assumptions")
    section = VALID_DEFINE[start:end]
    report = mutate(VALID_DEFINE, section, "")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert len(verdict.findings) == 1
    finding = verdict.findings[0]
    assert finding.rule == "RP.profile_missing"
    assert "medium" in finding.message


def test_malformed_yaml_is_treated_as_missing_profile() -> None:
    report = mutate(VALID_DEFINE, "  level: medium\n", ":{bad\n")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.profile_missing" in _rules(verdict)


def test_invalid_level_value_warns() -> None:
    report = mutate(VALID_DEFINE, "level: medium", "level: banana")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.level_invalid" in _rules(verdict)


def test_missing_level_field_warns() -> None:
    report = mutate(VALID_DEFINE, "  level: medium\n", "")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.level_invalid" in _rules(verdict)


def test_unknown_dimension_key_warns() -> None:
    report = mutate(VALID_DEFINE, "  dimensions:\n", "  dimensions:\n    cost: high\n")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.dimension_invalid" in _rules(verdict)


def test_invalid_dimension_value_warns() -> None:
    report = mutate(VALID_DEFINE, "security: medium", "security: banana")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.dimension_invalid" in _rules(verdict)


def test_override_applied_without_author_or_rationale_warns() -> None:
    report = mutate(VALID_DEFINE, "applied: false", "applied: true")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.override_unjustified" in _rules(verdict)


def test_override_applied_with_author_and_rationale_does_not_warn() -> None:
    report = mutate(VALID_DEFINE, "applied: false", "applied: true")
    report = mutate(
        report,
        "    author: null\n    rationale: null\n",
        '    author: "risk-team"\n    rationale: "documented justification"\n',
    )
    verdict = _lint(report)
    assert "RP.override_unjustified" not in _rules(verdict)


def test_level_below_declared_dimensions_warns() -> None:
    report = mutate(VALID_DEFINE, "level: medium", "level: low")
    report = mutate(report, "security: medium", "security: high")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "RP.level_below_dimensions" in _rules(verdict)


def test_level_above_declared_dimensions_does_not_warn() -> None:
    # Higher is allowed — elevation floors may raise the level above the
    # maximum dimension value; only a level BELOW the max dimension warns.
    report = mutate(VALID_DEFINE, "level: medium", "level: high")
    verdict = _lint(report)
    assert "RP.level_below_dimensions" not in _rules(verdict)


def test_every_rp_problem_at_once_stays_warn_never_fail() -> None:
    report = mutate(VALID_DEFINE, "level: medium", "level: banana")
    report = mutate(report, "  dimensions:\n", "  dimensions:\n    cost: high\n")
    report = mutate(report, "security: medium", "security: banana")
    report = mutate(report, "applied: false", "applied: true")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    rules = _rules(verdict)
    assert "RP.level_invalid" in rules
    assert "RP.dimension_invalid" in rules
    assert "RP.override_unjustified" in rules


def test_missing_required_section_still_fails() -> None:
    start = VALID_DEFINE.index("## Out of Scope")
    end = VALID_DEFINE.index("## Constraints")
    section = VALID_DEFINE[start:end]
    report = mutate(VALID_DEFINE, section, "")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    section_findings = [f for f in verdict.findings if f.rule == "L2.required_section"]
    assert any(f.field == "out_of_scope" for f in section_findings)


def test_risk_profile_heading_variant_still_parses() -> None:
    report = mutate(VALID_DEFINE, "## Risk Profile\n", "## Risk Profile (prospective)\n")
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_required_section_at_other_heading_levels_still_counts() -> None:
    report = mutate(VALID_DEFINE, "## Out of Scope", "### Out of Scope")
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert not any(f.rule == "L2.required_section" for f in verdict.findings)


def test_override_applied_quoted_false_is_not_treated_as_applied() -> None:
    report = mutate(VALID_DEFINE, "applied: false", 'applied: "false"')
    verdict = _lint(report)
    assert not any(f.rule == "RP.override_unjustified" for f in verdict.findings)
