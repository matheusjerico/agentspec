from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from spec_linter import cli
from spec_linter.contracts.feature_bundle import (
    FeatureBundle,
    FeatureBundleContract,
    load_feature_bundle,
)
from spec_linter.engine import lint
from spec_linter.verdict import Level

DEFINE = """# DEFINE: Sample
| Attribute | Value |
|---|---|
| **Feature** | SAMPLE |

| ID | Priority | Goal |
|----|----------|------|
| REQ-001 | MUST | Works |
"""
DESIGN = """# DESIGN: Sample
| Attribute | Value |
|---|---|
| **Feature** | SAMPLE |

## Task Manifest (v2)
```yaml
task_manifest:
  tasks:
    - id: TASK-CODE-001
```
## Traceability Matrix
| # | REQ | Priority | Tasks |
|---|-----|----------|-------|
| 1 | REQ-001 | MUST | TASK-CODE-001 |
"""
BUILD = """# BUILD REPORT: Sample
| Attribute | Value |
|---|---|
| **Feature** | SAMPLE |

## Task Execution with Agent Attribution
| # | Task ID | Status |
|---|---------|--------|
| 1 | TASK-CODE-001 | complete |
## Traceability Matrix
| # | REQ | Priority | Tasks | Tests | Verification Type | Result |
|---|-----|----------|-------|-------|-------------------|--------|
| 1 | REQ-001 | MUST | TASK-CODE-001 | pytest | unit | Pass |
"""


def pr_ready(feature: str = "SAMPLE") -> str:
    checks = {
        name: {
            "result": result,
            "evidence": {
                "source": "artifact",
                "reference": f"BUILD_REPORT_SAMPLE.md#{name}",
            },
        }
        for name, result in {
            "working_tree_clean": "pass",
            "base_resolved": "pass",
            "lint": "pass",
            "types": "not_configured",
            "tests": "pass",
            "build": "pass",
            "must_requirements_covered": "pass",
            "branch_verdict": "clean",
            "blocking_findings_open": "pass",
            "verdict_unchanged": "pass",
            "migration_plan": "not_applicable",
            "rollback_plan": "not_applicable",
            "residual_risks": "pass",
        }.items()
    }
    data = {
        "pr_ready": {
            "schema_version": 1,
            "feature": feature,
            "generated_at": datetime.now(UTC).isoformat(),
            "ship_head_sha": "a" * 40,
            "target_branch": "main",
            "target_tip_sha": "b" * 40,
            "checks": checks,
        }
    }
    return (
        f"# PR READY: {feature}\n\n"
        f"| Attribute | Value |\n|---|---|\n| **Feature** | {feature} |\n\n"
        f"```yaml\n{yaml.safe_dump(data, sort_keys=False)}```\n\nREQ-001"
    )


SHIPPED = """# SHIPPED: Sample
| Attribute | Value |
|---|---|
| **Feature** | SAMPLE |

Shipped: REQ-001
"""


def test_valid_bundle_passes() -> None:
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN, BUILD, SHIPPED, pr_ready()),
        FeatureBundleContract(),
    )
    assert verdict.level is Level.PASS


def test_missing_define_requirement_in_design_fails() -> None:
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN.replace("REQ-001", "REQ-002"), BUILD),
        FeatureBundleContract(),
    )
    assert "FB.define_requirement_missing_in_design" in [f.rule for f in verdict.findings]


def test_design_task_missing_in_build_fails() -> None:
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN, BUILD.replace("TASK-CODE-001", "TASK-OTHER-001")),
        FeatureBundleContract(),
    )
    assert "FB.design_task_missing_in_build" in [f.rule for f in verdict.findings]


def test_release_artifact_requirement_drift_fails() -> None:
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN, BUILD, SHIPPED.replace("REQ-001", "REQ-999")),
        FeatureBundleContract(),
    )
    assert "FB.shipped_requirement_drift" in [f.rule for f in verdict.findings]


def test_feature_bundle_cli_passes_valid_directory(tmp_path: Path) -> None:
    (tmp_path / "DEFINE_SAMPLE.md").write_text(DEFINE)
    (tmp_path / "DESIGN_SAMPLE.md").write_text(DESIGN)
    (tmp_path / "BUILD_REPORT_SAMPLE.md").write_text(BUILD)
    assert cli.main(["--feature-bundle", str(tmp_path)]) == 0


def test_empty_bundle_is_rejected() -> None:
    verdict = lint(FeatureBundle("", "", ""), FeatureBundleContract())
    assert verdict.level is Level.FAIL
    assert "FB.empty_artifact" in {finding.rule for finding in verdict.findings}


def test_placeholder_documents_without_real_structure_are_rejected() -> None:
    verdict = lint(
        FeatureBundle("REQ-001 MUST", "REQ-001 TASK-CODE-001", "REQ-001 TASK-CODE-001"),
        FeatureBundleContract(),
    )
    assert verdict.level is Level.FAIL
    assert "FB.artifact_structure" in {finding.rule for finding in verdict.findings}


def test_feature_identity_must_be_consistent() -> None:
    other_design = DESIGN.replace("| SAMPLE |", "| OTHER |", 1)
    verdict = lint(FeatureBundle(DEFINE, other_design, BUILD), FeatureBundleContract())
    assert "FB.feature_identity_drift" in {finding.rule for finding in verdict.findings}


def test_pr_ready_is_composed_with_its_individual_contract() -> None:
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN, BUILD, SHIPPED, "# PR READY: Sample\nREQ-001"),
        FeatureBundleContract(),
    )
    assert verdict.level is Level.FAIL
    assert "PR.artifact.unparseable" in {finding.rule for finding in verdict.findings}


def test_pr_ready_machine_feature_must_match_bundle_identity() -> None:
    artifact = pr_ready().replace("  feature: SAMPLE", "  feature: OTHER")
    verdict = lint(
        FeatureBundle(DEFINE, DESIGN, BUILD, SHIPPED, artifact),
        FeatureBundleContract(),
    )
    assert "FB.feature_identity_drift" in {finding.rule for finding in verdict.findings}


def test_release_mode_requires_shipped_and_pr_ready() -> None:
    verdict = lint(FeatureBundle(DEFINE, DESIGN, BUILD), FeatureBundleContract(release=True))
    assert verdict.level is Level.FAIL
    assert {"FB.release_shipped_required", "FB.release_pr_ready_required"} <= {
        finding.rule for finding in verdict.findings
    }


def test_loader_requires_pr_ready_to_be_passed_explicitly(tmp_path: Path) -> None:
    (tmp_path / "DEFINE_SAMPLE.md").write_text(DEFINE)
    (tmp_path / "DESIGN_SAMPLE.md").write_text(DESIGN)
    (tmp_path / "BUILD_REPORT_SAMPLE.md").write_text(BUILD)
    (tmp_path / "PR_READY_SAMPLE.md").write_text(pr_ready())
    assert load_feature_bundle(tmp_path).pr_ready is None


def test_release_cli_accepts_external_pr_ready(tmp_path: Path) -> None:
    bundle = tmp_path / "archive" / "SAMPLE"
    bundle.mkdir(parents=True)
    (bundle / "DEFINE_SAMPLE.md").write_text(DEFINE)
    (bundle / "DESIGN_SAMPLE.md").write_text(DESIGN)
    (bundle / "BUILD_REPORT_SAMPLE.md").write_text(BUILD)
    (bundle / "SHIPPED_2026-07-30.md").write_text(SHIPPED)
    report = tmp_path / "reports" / "PR_READY_SAMPLE.md"
    report.parent.mkdir()
    report.write_text(pr_ready())
    assert (
        cli.main(
            [
                "--feature-bundle",
                str(bundle),
                "--pr-ready",
                str(report),
                "--bundle-mode",
                "release",
            ]
        )
        == 0
    )
