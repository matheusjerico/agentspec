from __future__ import annotations

import subprocess
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from tools.release_gate import (
    ReleaseEvidenceError,
    _bound_path,
    validate_release_evidence,
)

ROOT = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


@pytest.fixture
def release_repo(tmp_path: Path) -> tuple[Path, Path, dict]:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "release@example.com")
    git(tmp_path, "config", "user.name", "Release Test")
    (tmp_path / "seed").write_text("seed")
    git(tmp_path, "add", "seed")
    git(tmp_path, "commit", "-m", "seed")
    sha = git(tmp_path, "rev-parse", "HEAD")
    benchmark = tmp_path / "benchmark.json"
    dogfoods = []
    for number in range(5):
        feature = f"DOGFOOD_{number}"
        bundle = tmp_path / "archive" / feature
        bundle.mkdir(parents=True)
        metadata = (
            f"# {{kind}}: {feature}\n\n## Metadata\n\n"
            "| Attribute | Value |\n|---|---|\n"
            f"| **Feature** | {feature} |\n\n"
        )
        (bundle / f"DEFINE_{feature}.md").write_text(
            metadata.format(kind="DEFINE")
            + "| ID | Priority | Goal |\n|---|---|---|\n"
            "| REQ-001 | MUST | Works |\n"
        )
        (bundle / f"DESIGN_{feature}.md").write_text(
            metadata.format(kind="DESIGN")
            + "## Task Manifest (v2)\n\n```yaml\n"
            "task_manifest:\n  tasks:\n    - id: TASK-CODE-001\n```\n\n"
            "## Traceability Matrix\n\n"
            "| # | REQ | Priority | Tasks |\n|---|---|---|---|\n"
            "| 1 | REQ-001 | MUST | TASK-CODE-001 |\n"
        )
        (bundle / f"BUILD_REPORT_{feature}.md").write_text(
            metadata.format(kind="BUILD REPORT")
            + "## Task Execution with Agent Attribution\n\n"
            "| # | Task ID | Status |\n|---|---|---|\n"
            "| 1 | TASK-CODE-001 | complete |\n\n"
            "## Traceability Matrix\n\n"
            "| # | REQ | Priority | Tasks | Tests | Verification Type | Result |\n"
            "|---|---|---|---|---|---|---|\n"
            "| 1 | REQ-001 | MUST | TASK-CODE-001 | pytest | unit | Pass |\n"
        )
        (bundle / "SHIPPED_2026-07-30.md").write_text(
            metadata.format(kind="SHIPPED") + "Delivered REQ-001.\n"
        )
        evidence = {"source": "artifact", "reference": "verified fixture"}
        checks = {
            name: {"result": result, "evidence": evidence}
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
        pr_ready = tmp_path / "reports" / f"PR_READY_{feature}.md"
        pr_ready.parent.mkdir(exist_ok=True)
        pr_ready.write_text(
            metadata.format(kind="PR READY")
            + "Requirements delivered: REQ-001.\n\n"
            + "```yaml\n"
            + yaml.safe_dump(
                {
                    "pr_ready": {
                        "schema_version": 1,
                        "feature": feature,
                        "generated_at": datetime.now(UTC).isoformat(),
                        "ship_head_sha": sha,
                        "target_branch": "main",
                        "target_tip_sha": sha,
                        "checks": checks,
                    }
                },
                sort_keys=False,
            )
            + "```\n"
        )
        dogfoods.append(
            {
                "feature": feature,
                "bundle": str(bundle.relative_to(tmp_path)),
                "pr_ready": str(pr_ready.relative_to(tmp_path)),
                "verification_commit": sha,
                "bundle_verdict": "pass",
            }
        )
    data = {
        "schema_version": 1,
        "decision": "go",
        "generated_at": datetime.now(UTC).isoformat(),
        "release_source_commit": sha,
        "benchmark": {
            "report": "benchmark.json",
            "framework": "agentspec",
            "scores": {
                "correctness": 100,
                "requirements_planning": 95,
                "tests": 95,
                "code_quality": 94,
                "review_pr": 100,
                "efficiency": 80,
            },
            "duration_seconds": 3000,
            "acceptance_passed": True,
        },
        "dogfoods": dogfoods,
    }
    benchmark.write_text(
        json.dumps(
            {
                "framework": "agentspec",
                "framework_source_commit": sha,
                "run": {
                    "scores": data["benchmark"]["scores"],
                    "duration_seconds": data["benchmark"]["duration_seconds"],
                },
                "acceptance": {
                    "all_passed": True,
                    "api": {"passed": 15, "total": 15},
                    "ui": {"passed": 2, "total": 2},
                },
            }
        )
    )
    report = tmp_path / "report.md"
    report.write_text(
        "# Release\n\n```yaml\n"
        + yaml.safe_dump({"production_readiness": data}, sort_keys=False)
        + "```\n"
    )
    return tmp_path, report, data


def test_valid_release_evidence_passes(release_repo: tuple[Path, Path, dict]) -> None:
    repo, report, _ = release_repo
    validate_release_evidence(report, repo)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("decision", "no-go", "decision"),
        ("generated_at", "never", "RFC3339"),
    ],
)
def test_invalid_top_level_evidence_fails(
    release_repo: tuple[Path, Path, dict], field: str, value: object, message: str
) -> None:
    repo, report, data = release_repo
    data[field] = value
    report.write_text(
        "```yaml\n"
        + yaml.safe_dump({"production_readiness": data}, sort_keys=False)
        + "```\n"
    )
    with pytest.raises(ReleaseEvidenceError, match=message):
        validate_release_evidence(report, repo)


def test_duplicate_dogfood_fails(release_repo: tuple[Path, Path, dict]) -> None:
    repo, report, data = release_repo
    data["dogfoods"][1]["feature"] = data["dogfoods"][0]["feature"]
    report.write_text(
        "```yaml\n"
        + yaml.safe_dump({"production_readiness": data}, sort_keys=False)
        + "```\n"
    )
    with pytest.raises(ReleaseEvidenceError, match="duplicate"):
        validate_release_evidence(report, repo)


def test_score_below_floor_fails(release_repo: tuple[Path, Path, dict]) -> None:
    repo, report, data = release_repo
    data["benchmark"]["scores"]["tests"] = 94
    report.write_text(
        "```yaml\n"
        + yaml.safe_dump({"production_readiness": data}, sort_keys=False)
        + "```\n"
    )
    with pytest.raises(ReleaseEvidenceError, match="below"):
        validate_release_evidence(report, repo)


def test_make_release_gate_uses_semantic_validator() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "python3 tools/release_gate.py" in makefile
    assert "grep -Eq '^## (Go|No-Go) Decision'" not in makefile
    assert "SHIPPED_2026-07-30" not in makefile


def test_bound_path_rejects_symlink_before_resolution(tmp_path: Path) -> None:
    target = tmp_path / "mutable.json"
    target.write_text("{}")
    link = tmp_path / "benchmark.json"
    link.symlink_to(target.name)

    with pytest.raises(ReleaseEvidenceError, match="symlink"):
        _bound_path(
            tmp_path,
            "benchmark.json",
            kind="benchmark",
            require_tracked=False,
        )
