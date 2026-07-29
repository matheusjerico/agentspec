"""BR.metrics_* rules (Increment 9) — the workflow_metrics block validator.

Written RED-first (TDD required: medium risk, logic-bearing linter code).
Five rules, armed by the constructor's `metrics_config` (None default keeps
every pre-Increment-9 constructor call green):

- BR.metrics_missing     configured + no Workflow Metrics yaml block → the
                         caller-supplied legacy level (WARN warn-mode /
                         FAIL fail-mode) — the mid-migration adoption path
- BR.metrics_parseable   fence present but yaml error / non-mapping /
                         missing workflow_metrics root key → FAIL
- BR.metrics_schema_version  block version != contract version → FAIL
- BR.metrics_key_shape   catalog key absent, or unknown top-level key → FAIL
- BR.metrics_fabricated  bare null (not {value: null, reason: ...}), empty
                         reason, or an estimate marker in a measured value
                         → FAIL; `reason` prose is exempt from the marker scan
"""

from __future__ import annotations

from spec_linter.contracts.build_report import BuildReportContract
from spec_linter.engine import lint
from spec_linter.verdict import Level, Verdict

from test_build_report_contract import (
    FIX_BUDGET,
    REQUIRED_SECTIONS,
    SCHEMA_VERSION,
    TDD_MODE_VALUES,
    VALID_REPORT,
    VERDICTS,
    mutate,
)

METRICS_CATALOG = [
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

METRICS_SECTION = """\

## Workflow Metrics

```yaml
workflow_metrics:
  schema_version: 1
  feature: "SAMPLE_FEATURE"
  phase_duration_seconds: { build: 2551 }
  time_to_first_green_seconds: { value: null, reason: "not instrumented" }
  task_count: 6
  effective_parallelism: 1
  tests_by_type: { unit: 8, contract: 2, documental: 4, integration: 0 }
  reopened_tasks: 0
  fix_rounds: { local: 1, final: 1 }
  findings: { critical: 0, important: 2, minor: 5, by_stage: { task_review: 3, branch_review: 4 } }
  requirements: { must_total: 6, must_verified: 6, excepted: 0 }
  operational_skips: ["J:exit3"]
  risk_overrides: 0
  tokens_cost: { value: null, reason: "platform does not expose reliable per-run tokens" }
```
"""

VALID_METRICS_REPORT = VALID_REPORT + METRICS_SECTION


def _contract(
    legacy_level: Level = Level.WARN,
    metrics_config: dict | None = None,
) -> BuildReportContract:
    return BuildReportContract(
        required_sections=REQUIRED_SECTIONS,
        verdicts=VERDICTS,
        fix_budget=FIX_BUDGET,
        schema_version=SCHEMA_VERSION,
        tdd_mode_values=TDD_MODE_VALUES,
        legacy_level=legacy_level,
        metrics_config=metrics_config,
    )


def _metrics_contract(legacy_level: Level = Level.WARN) -> BuildReportContract:
    return _contract(
        legacy_level=legacy_level,
        metrics_config={"schema_version": 1, "catalog": METRICS_CATALOG},
    )


def _lint(report: str, legacy_level: Level = Level.WARN) -> Verdict:
    return lint(report, _metrics_contract(legacy_level))


def _metrics_findings(verdict: Verdict) -> list:
    return [f for f in verdict.findings if f.rule.startswith("BR.metrics")]


def test_valid_metrics_block_passes() -> None:
    verdict = _lint(VALID_METRICS_REPORT)
    assert _metrics_findings(verdict) == []
    assert verdict.level is Level.PASS


def test_bare_null_fails_naming_the_key() -> None:
    report = mutate(VALID_METRICS_REPORT, "reopened_tasks: 0", "reopened_tasks: null")
    verdict = _lint(report)
    findings = _metrics_findings(verdict)
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert findings[0].level is Level.FAIL
    assert "reopened_tasks" in findings[0].message


def test_tilde_null_shorthand_also_fails() -> None:
    report = mutate(VALID_METRICS_REPORT, "risk_overrides: 0", "risk_overrides: ~")
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]


def test_null_without_reason_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        'time_to_first_green_seconds: { value: null, reason: "not instrumented" }',
        "time_to_first_green_seconds: { value: null }",
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert "time_to_first_green_seconds" in findings[0].message


def test_null_with_empty_reason_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        'time_to_first_green_seconds: { value: null, reason: "not instrumented" }',
        'time_to_first_green_seconds: { value: null, reason: "" }',
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]


def test_estimate_marker_in_measured_value_fails() -> None:
    report = mutate(VALID_METRICS_REPORT, "task_count: 6", 'task_count: "approx 6"')
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert "task_count" in findings[0].message


def test_tilde_prefixed_string_value_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        "phase_duration_seconds: { build: 2551 }",
        'phase_duration_seconds: { build: "~2500" }',
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]


def test_reason_prose_is_exempt_from_the_estimate_scan() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        'reason: "not instrumented"',
        'reason: "estimated timers are forbidden here, so this stays null"',
    )
    assert _metrics_findings(_lint(report)) == []


def test_schema_version_mismatch_fails() -> None:
    report = mutate(VALID_METRICS_REPORT, "schema_version: 1", "schema_version: 2")
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_schema_version"]
    assert findings[0].level is Level.FAIL


def test_unknown_top_level_key_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT, "risk_overrides: 0", "risk_overrides: 0\n  vibe_score: 10"
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_key_shape"]
    assert "vibe_score" in findings[0].message


def test_missing_catalog_key_fails() -> None:
    report = mutate(VALID_METRICS_REPORT, "  risk_overrides: 0\n", "")
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_key_shape"]
    assert "risk_overrides" in findings[0].message


def test_unparseable_fence_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        "workflow_metrics:\n  schema_version: 1",
        "workflow_metrics: [unclosed\n  schema_version: 1",
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_parseable"]
    assert findings[0].level is Level.FAIL


def test_fence_without_root_key_fails() -> None:
    report = mutate(VALID_METRICS_REPORT, "workflow_metrics:", "other_metrics:")
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_parseable"]


def test_absent_section_is_the_legacy_level_warn() -> None:
    verdict = lint(VALID_REPORT, _metrics_contract(legacy_level=Level.WARN))
    findings = _metrics_findings(verdict)
    assert [f.rule for f in findings] == ["BR.metrics_missing"]
    assert findings[0].level is Level.WARN


def test_absent_section_is_the_legacy_level_fail() -> None:
    verdict = lint(VALID_REPORT, _metrics_contract(legacy_level=Level.FAIL))
    findings = _metrics_findings(verdict)
    assert [f.rule for f in findings] == ["BR.metrics_missing"]
    assert findings[0].level is Level.FAIL


def test_unconfigured_contract_never_emits_metrics_findings() -> None:
    # None default — pre-Increment-9 constructor calls and repos without the
    # workflow_metrics block see zero BR.metrics_* findings either way.
    assert _metrics_findings(lint(VALID_REPORT, _contract())) == []
    assert _metrics_findings(lint(VALID_METRICS_REPORT, _contract())) == []


def test_legacy_report_skips_metrics_rules() -> None:
    legacy = mutate(VALID_METRICS_REPORT, "| **Schema Version** | 2 |\n", "")
    verdict = _lint(legacy)
    assert _metrics_findings(verdict) == []
    assert "BR.legacy_report" in [f.rule for f in verdict.findings]


def test_unfilled_template_placeholder_fails() -> None:
    # Review F1 (Critical): a verbatim, unfilled copy of the template
    # skeleton must never PASS the anti-fabrication rule.
    report = mutate(
        VALID_METRICS_REPORT, 'feature: "SAMPLE_FEATURE"', 'feature: "{FEATURE_NAME}"'
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert "placeholder" in findings[0].message


def test_unfilled_placeholder_in_reason_also_fails() -> None:
    report = mutate(
        VALID_METRICS_REPORT,
        'reason: "not instrumented"',
        'reason: "{why not measured}"',
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]


def test_sibling_reason_named_key_is_not_exempt() -> None:
    # Review F2 (Important): the reason exemption is shape-aware — a
    # measured key that merely ENDS in "reason" gets the marker scan.
    report = mutate(
        VALID_METRICS_REPORT,
        "findings: { critical: 0, important: 2, minor: 5, by_stage: { task_review: 3, branch_review: 4 } }",
        'findings: { critical: 0, important: 2, minor: 5, by_stage: { task_review: 3, branch_review: 4 }, override_reason: "approx 5" }',
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert "override_reason" in findings[0].message


def test_availability_mapping_is_closed_to_value_and_reason() -> None:
    # Review F3 (Important): extra keys cannot ride the availability mapping.
    report = mutate(
        VALID_METRICS_REPORT,
        'time_to_first_green_seconds: { value: null, reason: "not instrumented" }',
        'time_to_first_green_seconds: { value: null, reason: "not instrumented", confidence: "approx 90%" }',
    )
    findings = _metrics_findings(_lint(report))
    assert [f.rule for f in findings] == ["BR.metrics_fabricated"]
    assert "confidence" in findings[0].message
