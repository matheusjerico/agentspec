from __future__ import annotations

import subprocess
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from spec_linter.contracts.pr_readiness import (
    PrReadyArtifactContract,
    PrReadinessRuntimeValidator,
)
from spec_linter.engine import lint
from spec_linter.verdict import Level


CHECKS = {
    name: {
        "result": result,
        "evidence": {
            "source": "artifact",
            "reference": f"BUILD_REPORT.md#{name}",
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


def artifact(
    sha: str = "a" * 40,
    target: str = "main",
    *,
    generated_at: str | None = None,
    checks: dict[str, object] | None = None,
    **extra: object,
) -> str:
    data = {
        "pr_ready": {
            "schema_version": 1,
            "feature": "TEST",
            "generated_at": generated_at or datetime.now(UTC).isoformat(),
            "ship_head_sha": sha,
            "target_branch": target,
            "target_tip_sha": sha,
            "checks": checks or CHECKS,
            **extra,
        }
    }
    return f"```yaml\n{yaml.safe_dump(data, sort_keys=False)}```"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def test_artifact_contract_accepts_exact_catalog() -> None:
    assert lint(artifact(), PrReadyArtifactContract()).level == Level.PASS


def test_artifact_contract_fails_missing_check() -> None:
    text = artifact().replace("    tests:\n", "    omitted_tests:\n")
    verdict = lint(text, PrReadyArtifactContract())
    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.checks_shape" for f in verdict.findings)


def test_artifact_contract_fails_multiple_roots() -> None:
    text = artifact()
    assert lint(text + "\n" + text, PrReadyArtifactContract()).level == Level.FAIL


@pytest.mark.parametrize(
    ("location", "extra"),
    [
        ("root", {"unexpected": "value"}),
        ("check", {"unexpected": "value"}),
    ],
)
def test_artifact_contract_rejects_unknown_keys(location: str, extra: dict[str, str]) -> None:
    checks = deepcopy(CHECKS)
    root_extra: dict[str, object] = {}
    if location == "root":
        root_extra = extra
    else:
        checks["tests"].update(extra)

    verdict = lint(artifact(checks=checks, **root_extra), PrReadyArtifactContract())

    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.extra_keys" for f in verdict.findings)


@pytest.mark.parametrize(
    "generated_at",
    [
        "2026-07-30 12:00:00",
        "2026-07-30T12:00:00",
        "not-a-date",
    ],
)
def test_artifact_contract_requires_rfc3339_timestamp(generated_at: str) -> None:
    verdict = lint(artifact(generated_at=generated_at), PrReadyArtifactContract())
    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.generated_at" for f in verdict.findings)


def test_artifact_contract_rejects_stale_timestamp() -> None:
    now = datetime(2026, 7, 30, 12, tzinfo=UTC)
    generated_at = (now - timedelta(hours=25)).isoformat()
    contract = PrReadyArtifactContract(now=lambda: now)

    verdict = lint(artifact(generated_at=generated_at), contract)

    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.artifact_stale" for f in verdict.findings)


@pytest.mark.parametrize(
    "evidence",
    [
        "pytest",
        {},
        {"source": "artifact"},
        {"source": "command", "command": "pytest"},
        {"source": "command", "command": "pytest", "exit_code": 1},
        {"source": "command", "command": "true", "exit_code": 0},
        {"source": "artifact", "reference": ""},
    ],
)
def test_artifact_contract_requires_strong_structured_evidence(
    evidence: object,
) -> None:
    checks = deepcopy(CHECKS)
    checks["tests"]["evidence"] = evidence

    verdict = lint(artifact(checks=checks), PrReadyArtifactContract())

    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.evidence_invalid" for f in verdict.findings)


def test_runtime_detects_dirty_head_and_failed_command(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked").write_text("one")
    git(tmp_path, "add", "tracked")
    git(tmp_path, "commit", "-m", "initial")
    sha = git(tmp_path, "rev-parse", "HEAD")
    parsed = PrReadyArtifactContract().parse(artifact(sha))
    (tmp_path / "tracked").write_text("dirty")
    findings = PrReadinessRuntimeValidator(
        tmp_path, test_command="false"
    ).check(parsed)
    rules = {f.rule for f in findings}
    assert "PR.working_tree_dirty" in rules
    assert "PR.tests_failed" in rules


def test_runtime_passes_clean_repository(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked").write_text("one")
    git(tmp_path, "add", "tracked")
    git(tmp_path, "commit", "-m", "initial")
    sha = git(tmp_path, "rev-parse", "HEAD")
    parsed = PrReadyArtifactContract().parse(artifact(sha))
    findings = PrReadinessRuntimeValidator(
        tmp_path,
        test_command="test -f tracked",
        build_command="test -f tracked",
    ).check(parsed)
    assert not [finding for finding in findings if finding.level == Level.FAIL]


@pytest.mark.parametrize("command", [None, "", "true", ":", "exit 0", "echo ok"])
def test_runtime_rejects_absent_or_trivial_test_command(
    tmp_path: Path, command: str | None
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked").write_text("one")
    git(tmp_path, "add", "tracked")
    git(tmp_path, "commit", "-m", "initial")
    parsed = PrReadyArtifactContract().parse(artifact(git(tmp_path, "rev-parse", "HEAD")))

    findings = PrReadinessRuntimeValidator(tmp_path, test_command=command).check(parsed)

    assert any(f.rule == "PR.tests_not_run" for f in findings)


@pytest.mark.parametrize(
    ("build_result", "build_command"),
    [
        ("pass", None),
        ("not_configured", "make build"),
    ],
)
def test_runtime_rejects_build_configuration_incoherence(
    tmp_path: Path, build_result: str, build_command: str | None
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked").write_text("one")
    git(tmp_path, "add", "tracked")
    git(tmp_path, "commit", "-m", "initial")
    checks = deepcopy(CHECKS)
    checks["build"]["result"] = build_result
    parsed = PrReadyArtifactContract().parse(
        artifact(git(tmp_path, "rev-parse", "HEAD"), checks=checks)
    )

    findings = PrReadinessRuntimeValidator(
        tmp_path,
        test_command="test -f tracked",
        build_command=build_command,
    ).check(parsed)

    assert any(f.rule == "PR.build_incoherent" for f in findings)
